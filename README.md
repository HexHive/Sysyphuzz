# SYSYPHUZZ and the Pressure of More Coverage

## Abstract
Kernel fuzzing effectively uncovers vulnerabilities. While existing kernel fuzzers primarily focus on maximizing code coverage, coverage alone does not guarantee thorough exploration. Moreover, existing fuzzers, aimed at maximizing coverage, have plateaued. This pressing situation highlights the need for a new direction: code frequency-oriented kernel fuzzing. However, increasing the exploration of low-frequency kernel code faces two key challenges: (1) Resource constraints make it hard to schedule sufficient tasks for low-frequency regions without causing task explosion. (2) Random mutations often break context dependencies of syscalls targeting low-frequency regions, reducing the effectiveness of fuzzing.

In our paper, we first perform a fine-grained study of imbalanced code coverage by evaluating Syzkaller in the Linux kernel and, as a response, propose SYSYPHUZZ, a kernel fuzzer designed to boost exploration of under-tested code regions. SYSYPHUZZ introduces Selective Task Scheduling to dynamically prioritize and manage exploration tasks, avoiding task explosion. It also employs Context-Preserving Mutation strategy to reduce the risk of disrupting important execution contexts.

## Citation
```bash
🚀 Coming Soon at NDSS 2026.
```

## Repo Structure
```bash
Sysyphuzz/
|--source_code
|  |--9750182a9a67f35e95cb1e077a3b69a4a9b54083_0110.diff  # This git diff file contains the changes needed to modify Syzkaller (commit: 9750182) to Sysyphuzz.
|  |--warmup_10_flag0107.go                               # This go file implements the essential components required to run Sysyphuzz.
|  |--syzbot_config                                       # The config file using for compileing the Linux kernel. (version: Linux/x86_64 6.12.0-rc6)
|  |--create-image.sh                                     # create-image.sh creates a minimal Debian Linux image suitable for syzkaller.
|  |--ci-qemu-upstream-corpus.db                          # A Syzbot corpus captured on November 13, 2024.
|  |--deploy.sh                                           # Run the deploy.sh script with sudo privileges. This script creates a new user fuzz and sets up the environment.
|  |--scripts
|  |  |--atifact_valuation.pdf                            # We provide this appendix to support artifact evaluation and facilitate smooth reproduction of our results.
|  |  |--...py                                            # Scripts for generating data used in the paper.
```

## How To Build SYSYPHUZZ

SYSYPHUZZ is based on Syzkaller, SYSYPHUZZ does not require additional dependencies.
### Clone this Repo
### Build 
Run the deploy.sh script with sudo privileges.
This script creates a new user fuzz and sets up the environment. 
You can modify the default password in the shell file if needed. 

Once executed, Sysyphuzz is ready for use.

## How to Use SYSYPHUZZ

SYSYPHUZZ is used in the same way as SYZKALLER, and is controlled by adding configuration options in the configuration file.

After running the deployment script,
two configuration files will be automatically generated and placed under:
```bash
/home/fuzz/code/sysyphuzz/
```

These are:
```bash
sysyphuzz.cfg – The main configuration file for running the Sysyphuzz system.

syzkaller.cfg – The baseline configuration used to run the vanilla Syzkaller fuzzer for comparison purposes.
```

These files are pre-populated with default settings but can be further customized.

### sysyphuzz.cfg
```bash
{
    "target": "linux/amd64",
    "http": "127.0.0.1:56743",
    "workdir": "/home/fuzz/code/sysyphuzz/workdir_sysy",
    "kernel_src": "/home/fuzz/kernel/linux",
    "kernel_obj": "/home/fuzz/kernel/linux-out",
    "raw_cover": true,
    "warm_up": true,
    "boost_only": false,
    "cover_bb_num" : "sysyphuzz_bb",
    "reproduce": false,
    "image": "/home/fuzz/Image/imag1/bullseye.img",
    "sshkey": "/home/fuzz/Image/imag1/bullseye.id_rsa",
    "syzkaller": "/home/fuzz/code/sysyphuzz",
    "procs": 4,
    "type": "qemu",
    "vm": {
        "count": 8,
        "cpu": 2,
        "mem": 4096,
        "kernel": "/home/fuzz/kernel/linux-out/arch/x86/boot/bzImage"
    }
}
```

In addition to the standard Syzkaller configuration options, Sysyphuzz introduces several new keywords in sysyphuzz.cfg to support advanced features:

|Keyword | Type | Description|
|---|---|---|
|warm_up | bool | Enables the warm-up stage to prioritize under-covered basic blocks (BBs).
|boost_only	| bool | Runs only the boosting phase, skipping all coverage feedback, this is a expert mode used for subsequent development, keep false here.
|cover_bb_num | string | Path to the directory tracking the number of times each BB has been covered.

All other configuration fields remain compatible with Syzkaller, making migration or extension straightforward.

Example: Enabling Warm-Up and Hit Count Logging
```bash
warm_up = true                             # Enables Sysyphuzz's warm-up mode to focus on under-covered BBs.
cover_bb_num = "./cover_bb_num_dir"        # Directory to store all log files tracking BB hit counts.
```

If the user does not wish to track hit counts (e.g., to save disk space), simply disable logging by setting:
```bash
cover_bb_num = "donotrecord"
```

💡 Note: Disabling hit count tracking can significantly reduce disk usage, which is useful when running on low-resource environments.

Example:
```bash
warm_up = true                                 # Fuzzer running as SYSYPHUZZ.
cover_bb_num = "./cover_bb_num_dir"            # All log files for hit count record will go into this folder.
```
Running in Syzkaller-Compatible Mode

By setting:
```bash
warm_up = false
```

Sysyphuzz will run in the default Syzkaller-compatible mode, without enabling any warm-up or boosting logic.

In this mode, the fuzzer behaves exactly like Syzkaller in terms of test execution and scheduling.
It will still record hit count information in parallel.
However, only observes coverage data passively and does not interfere with the fuzzing logic, maintaining compatibility with Syzkaller's original operation.

This is useful for:

* Baseline comparisons with hitcount-aware data.

* Enable the fuzzer to switch rapidly between the Syzkaller logic and the Sysyphuzz logic.

💡 Tip: To completely disable hit count logging and save memory/disk resources, use:

```bash
cover_bb_num = "donotrecord"
```

