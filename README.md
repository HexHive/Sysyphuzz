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


