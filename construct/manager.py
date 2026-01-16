import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(r"""
  _______ _            _____                 _                   _   
 |__   __| |          / ____|               | |                 | |  
    | |  | |__   ___ | |     ___  _ __   ___| |_ _ __ _   _  ___| |_ 
    | |  | '_ \ / _ \| |    / _ \| '_ \ / __| __| '__| | | |/ __| __|
    | |  | | | |  __/| |___| (_) | | | |\__ \ |_| |  | |_| | (__| |_ 
    |_|  |_| |_|\___| \_____\___/|_| |_||___/\__|_|   \__,_|\___|\__|
                                                                     
    [ The Construct: Zero-to-Hero Learning Environment ]
    """)

def main_menu():
    while True:
        clear_screen()
        print_banner()
        print("1. [BUILD]  Compile Kernel Module (Docker)")
        print("2. [DEPLOY] Provision Target VM (Vagrant)")
        print("3. [ATTACK] SSH into Target (Vagrant)")
        print("4. [STATUS] Check VM Status")
        print("5. Exit")
        
        choice = input("\nSelect an option: ")
        
        if choice == '1':
            print("\nBuilding Kernel Module...")
            os.system("docker build -t kernel-builder .")
            input("\nPress Enter to return...")
        elif choice == '2':
            print("\nProvisioning Target VM...")
            os.system("vagrant up")
            input("\nPress Enter to return...")
        elif choice == '3':
            print("\nConnecting to Target...")
            os.system("vagrant ssh")
        elif choice == '4':
            print("\nChecking Status...")
            os.system("vagrant status")
            input("\nPress Enter to return...")
        elif choice == '5':
            sys.exit()

if __name__ == "__main__":
    main_menu()
