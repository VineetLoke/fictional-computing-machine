# Zero-to-Hero: Systems Architect & Offensive Security Curriculum

**Role**: Technical Instructor & Systems Architect
**Tone**: Strict, Encouraging, Elite.

This curriculum is designed to take you from "user" to "architect" and finally to "breaker." You will layer your knowledge: first understanding how the machine thinks, then automating its operations, and finally exploiting its flaws.

---

## 🗺️ The Roadmap

### Phase 0: The Foundation (C Programming & Pointers)
**Objective**: Master the language of the kernel. You cannot write modules or exploit buffers without understanding memory addresses.

*   **Theory**: Variables vs Pointers, Memory addresses, Stack vs Heap, `malloc`/`free`, Pointer arithmetic.
*   **Practice**:
    *   **The Exam**: Implement a Linked List in C from scratch. Then implement a Double Linked List. If you crash (Segfault), start over.
*   **Resources**:
    *   *Book*: "The C Programming Language" (Kernighan & Ritchie) - The timeless classic.
    *   *Concept*: [Pointers in C - Great Tutorial](https://www.youtube.com/watch?v=zuegQmMdy8M) (or similar reliable guide).

### Phase 1: The Metal (Hardware & OS)
**Objective**: Understand the distinct layers of abstraction from silicon to shell. You cannot hack what you do not understand.

#### 1.1 Digital Logic & Architecture
*   **Theory**: Transistors, logic gates (AND, OR, NOT), CPU architecture (ALU, Registers, Bus), Memory hierarchy (L1/L2/L3, RAM), Fetch-Decode-Execute cycle.
*   **Practice**:
    *   **Nand2Tetris (Part 1)**: Build a computer from scratch starting with NAND gates.
    *   Write a simple "Hello World" in **Assembly (x86_64)** without libc (using syscalls directly).
*   **Checkpoint**: You understand exactly what happens physically when you press a key.

#### 1.2 Operating System Internals
*   **Theory**: Kernel mode vs. User mode, Process scheduling, Memory Management (Virtual Memory, Paging), Interrupts, File Systems (inodes, superblock).
*   **Practice**:
    *   **Linux From Scratch (LFS)**: Build a Linux system from source source codes. (Do at least Chapter 5 & 6).
    *   Write a **Linux Kernel Module (LKM)**: A simple "Character Device" that accepts input and virtually "stores" it.
*   **Resources**:
    *   *Book*: "Operating Systems: Three Easy Pieces" (OSTEP)
    *   *Book*: "Computer Systems: A Programmer's Perspective" (CS:APP)

### Phase 2: The Factory (DevOps & Infrastructure)
**Objective**: Treating infrastructure as code. Manual configuration is forbidden.

> [!WARNING]
> **The Environment Hell**: Setting up this phase (Vagrant/Docker/Hyper-V/WSL2 on Windows or Mac) is the hardest part for beginners. **This is not a bug; it is the job.** If you spend 3 days fixing a virtualization error, you have spent 3 days learning DevOps. Do not quit.

#### 2.1 Virtualization & Containers
*   **Theory**: Hypervisors (Type 1 vs Type 2), Namespaces & Cgroups (the magic behind Docker), Layered filesystems (OverlayFS).
*   **Practice**:
    *   **Docker**: Dockerize the Kernel Module build environment. Ensure the module compiles 100% reproducibly.
    *   **Vagrant/QEMU**: specific automation to spin up a headless Linux VM.
*   **Checkpoint**: You can destroy your local machine and restore your environment in minutes.

#### 2.2 CI/CD & Automation
*   **Theory**: Continuous Integration principles, Idempotency, Infrastructure as Code (IaC).
*   **Practice**:
    *   **GitHub Actions**: Write a pipeline that compiles your Kernel Module on every git push.
    *   **Ansible**: Write a playbook that targets your Vagrant VM, installs the new Kernel Module, and configures the networking.

### Phase 3: The Breaker (Ethical Hacking)
**Objective**: Weaponize your deep understanding of the previous two phases.

#### 3.1 Network Security
*   **Theory**: TCP/IP Handshake, OSI Model, Subnetting, ARP, DNS, Firewalls.
*   **Practice**:
    *   **Wireshark**: Capture your own traffic. Analyze a TLS handshake.
    *   **Nmap**: Scan your local network (DevOps lab) to see available services.

#### 3.2 Exploitation & Reverse Engineering
*   **Theory**: Stack vs Heap, Buffer Overflows, ROP chains, Shellcode, Privilege Escalation.
*   **Practice**:
    *   **Buffer Overflow**: Intentionally introduce a `strcpy` vulnerability in your Kernel Module from Phase 1.
    *   **Exploit Development**: Write a C/Python script to crash the kernel or escalate privileges on your deployed VM.
*   **Resources**:
    *   *Book*: "Hacking: The Art of Exploitation"
    *   *Site*: OverTheWire (Bandit & Narnia levels)

---

## 🏗️ Project: The "Unified Homelab"

This project connects all three domains. You will strictly follow this pipeline.

**Premise**: You are developing a high-performance "Message Storage" kernel driver, automating its deployment, and then auditing it for security flaws.

### Lab Architecture
*   **Host**: Your physical machine (Windows/Mac/Linux).
*   **Hypervisor**: VirtualBox or VMware Workstation Player (Free).
*   **Automation**: Vagrant (manages the VMs) + Docker (builds the code).
*   **Attacker**: Kali Linux VM.
*   **Target**: Ubuntu Server VM (Headless).

### The Pipeline Workflow

1.  **Develop (The Metal)**
    *   Write `vulnerable_driver.c`. It creates a device `/dev/vuln_vault`.
    *   It has a function `device_write` that uses `strcpy` (unsafe) instead of `strncpy`.
    *   Push code to GitHub.

2.  **Build (The Factory - CI)**
    *   GitHub Actions triggers on push.
    *   Spins up a **Docker** container.
    *   Compiles `vulnerable_driver.c` into `vulnerable_module.ko`.
    *   Uploads the `.ko` file as a build artifact.

3.  **Deploy (The Factory - CD)**
    *   On your local machine, run an **Ansible** playbook.
    *   Ansible talks to Vagrant, spins up the **Target VM**.
    *   Downloads the latest `.ko` artifact.
    *   `insmod vulnerable_module.ko`.
    *   Sets permissions so any user can write to `/dev/vuln_vault`.

4.  **Attack (The Breaker)**
    *   Boot your **Kali Linux VM**.
    *   Connect to the Target VM (simulate a compromised low-privilege user or network service).
    *   Interact with `/dev/vuln_vault`. Send a payload longer than the buffer.
    *   **Goal**: Abstract: cause a Kernel Panic (DoS). Advanced: Overwrite return address to execute shellcode (PrivEsc).

---

## 📚 The Vault of Resources

### Phase 1: Hardware & OS
*   **Books**:
    *   *Code: The Hidden Language of Computer Hardware and Software* by Charles Petzold (The absolute best start).
    *   *The Linux Programming Interface* by Michael Kerrisk (The API Bible).
*   **Websites**:
    *   [Nand2Tetris](https://www.nand2tetris.org/) (Free course).
    *   [OSDev.org Wiki](https://wiki.osdev.org/Main_Page) (For kernel dev).
*   **Communities**:
    *   r/osdev
    *   r/lowlevel

### Phase 2: DevOps
*   **Books**:
    *   *The Phoenix Project* (Gene Kim) - For the philosophy.
    *   *Kubernetes Up & Running* (O'Reilly).
*   **Websites**:
    *   [Roadmap.sh](https://roadmap.sh/devops) - Visual interactive path.
    *   [Katacoda (O'Reilly)](https://www.oreilly.com/online-learning/katacoda.html) - Browser-based labs.
*   **Communities**:
    *   r/devops
    *   r/homelab (Crucial for hardware/networking setups).

### Phase 3: Ethical Hacking
*   **Books**:
    *   *The Web Application Hacker's Handbook* (Stuttard & Pinto).
    *   *Hacking: The Art of Exploitation* (Jon Erickson) - C & Assembly focus.
*   **Websites**:
    *   [OverTheWire](https://overthewire.org/wargames/) (Start with Bandit).
    *   [HackTheBox](https://www.hackthebox.com/) (Academy is excellent).
    *   [Pwn.college](https://pwn.college/) (University-grade binary exploitation).
*   **Communities**:
    *   r/securityCTF
    *   r/netsec (Strictly professional discussions).

---

**Final Instruction**: This path is not linear; it is circular. The better you understand the OS (Phase 1), the better you can break it (Phase 3). The better you can automate (Phase 2), the faster you can learn.

**Start now.** Good luck.
