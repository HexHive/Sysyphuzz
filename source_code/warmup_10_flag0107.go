// Copyright 2024 renzezhong. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE.

package fuzzer

import (
	"sync/atomic"
	"github.com/google/syzkaller/pkg/flatrpc"
	"github.com/google/syzkaller/pkg/log"
)

type warmupCall struct{
	warmedBBs []uint64
}


//  keeps track of the choosen BBset, which is under-covered.
type Warmup struct {
	UnderCoverBBSet atomic.Value //Atomic map for undercovered BBs
	DenyList map[uint64]Info
}
type Info struct{
	HitNum uint32
	ChooseTime uint32
	Deny bool
}

func newWarmup() *Warmup{
	WarmupIns := &Warmup{}
	WarmupIns.UnderCoverBBSet.Store(make(map[uint64]bool))
	WarmupIns.DenyList = make(map[uint64]Info)
	return WarmupIns
}

func (warmup *Warmup) DenyCheck(tmpBBSet map[uint64]bool, pcHitMap map[uint64]uint32) uint32{
	if tmpBBSet == nil || pcHitMap == nil || len(warmup.DenyList) == 0 {
		return 0
	}
	var denyNum uint32
	for k := range tmpBBSet{
		if info, exists := warmup.DenyList[k]; exists {
			// In the deny list and no hit number changed, deny it.
			if hitCount, hitExists := pcHitMap[k]; hitExists{
				if info.HitNum == hitCount && info.Deny {
					//delete(tmpBBSet, k)
					tmpBBSet[k] = false
					denyNum += 1
				} else if info.Deny{
					// In the deny list but hit number changed, remove it from the deny list
					info.Deny = false
					info.HitNum = hitCount
					info.ChooseTime = 0
					warmup.DenyList[k] = info
					tmpBBSet[k] = true
				}
			}
		}
	}
	return denyNum
}

func (warmup *Warmup) UpdateDenyList(tmpBBSet map[uint64]bool, pcHitMap map[uint64]uint32) uint32 {
	if tmpBBSet == nil || pcHitMap == nil {
		return 0
	}
	for k, info := range warmup.DenyList{
		if hitCount, exists := pcHitMap[k]; exists { 
			if info.HitNum == hitCount{
				info.ChooseTime += 1
				if info.ChooseTime > 10{
					info.Deny = true
				}
			} else {
				info.HitNum = hitCount
				info.ChooseTime = 0
				info.Deny = false
			}
			warmup.DenyList[k] = info
		}
	}
	
	for k, ifuse := range tmpBBSet{
		if _, exists := warmup.DenyList[k]; !exists && ifuse{
			if hitCount, exists := pcHitMap[k]; exists{
				warmup.DenyList[k] = Info{HitNum: hitCount, ChooseTime: 0, Deny: false}
			}
		}
	}

	return uint32(len(warmup.DenyList))
}

func (warmup *Warmup) Update(tmpBBSet map[uint64]bool){
	warmup.UnderCoverBBSet.Store(tmpBBSet)
}

func (warmup *Warmup) CheckPerCall(info *flatrpc.CallInfo, call int, warmupcalls *map[int]*warmupCall){
	if info == nil{
		log.Logf(0, "No execution result")
		return
	}
	//log.Logf(0, "the covered bb number for this request is :%d", len(info.Cover))
	overlapBBs := warmup.findOverlap(info.Cover) 
	if len(overlapBBs) == 0{
		log.Logf(0, "No overlap")
		return
	}
	if *warmupcalls == nil{
		*warmupcalls = make(map[int]*warmupCall)
	}
	(*warmupcalls)[call] = &warmupCall{
		warmedBBs: overlapBBs,
	}
	log.Logf(0, "The overlapped bb 's number between this request and the undercovered BBs is :%d", len(overlapBBs))
	
}


func (warmup *Warmup) findOverlap(coveredBBs []uint64) []uint64{
	var overlapBBs []uint64
	currentBBSet := warmup.UnderCoverBBSet.Load().(map[uint64]bool)
	//log.Logf(0, "Selected BBs number are %v, covered BBs number are %v", len(currentBBSet), len(coveredBBs))
	for _, bb := range coveredBBs{
		if _, exists :=  currentBBSet[bb]; exists{
			overlapBBs = append(overlapBBs, bb)
		}
	}
	return overlapBBs
}


