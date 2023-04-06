# pret manager

This is a tool to help people maintain various [pret disassemblies](https://github.com/pret) and hacks derived from them.

  * **Currently for Gen 1/2 Only**

There are 4 text files which are lists of repositories that this tool can manage.
  * pret
    * The four Gen 1/2 pret disassemblies
  * forks
    * Hacks made using disassemblies
  * hacks
    * Hacks made using binary hacking (and the repo hosts versions)
  * extra
    * Other Gen 1 related repositories

Each line refers to a specific repository, with the follow comma-separated values:
  * URL to github repository
  * Original disassembly it is based on
  * RGBDS build version to use for building (optional)
    * If not provided, it will not attempt to build

Note that the 2nd and 3rd values are only applicable to repositories that are disassemblies.

In addition, you can make a 'custom.txt' for any othe repos you want to manage, and it will not be overwritten by pulls

## Requirements

The follow programs are needed:
  * python (3.7+)
  * git (2.4+)
  * gh (Github CLI)

If Windows:
  * wsl
    * within wsl, see Linux reqs

If Linux:
  * make (& dependencies required to build rgbds & pret disassemblies)

## Usage

To run, enter the repository in a shell and enter:

`python manage.py <repositories> <command>`

### Repositories

This will select what repositories to manage.

  * -dir, -d
    * Path(s) of directories to manage
  * -remote' -r
    * URL(s) of remote repositories to manage
    * Note that this will only work repositories that already exist locally
      * To add a new remote repository, add a line to 'custom.txt'
  * -glob, -g
    * glob pattern of directories to manage

If no repositories are provided, it will apply the commands on all repositories

### Commands

This will dictate what commands will be applied to the managed reopsitories

  * -update, -u
    * Pull (or clone) the managed repositories
  * -build, -b
    * Build the managed repositories
    * Additional arguments can be provided to select specific branch/commit
  * -clean, -c
    * Clean the managed repositories
  * -verbose, -v
    * Display all log messages


If no commands are provided, it will first execute **update** followed by **build**

## Potential Future Work
  * Option to clean and retry for failed builds
    * Option to mark as failed and wont attempt to build again unless unmarked
  * Allow users to point to own rgbds directory in config file
  * Launch game in emulator
    * Allow users to point emulator in config file
  * Organize based on major/minor hacks
    * Or, based on how many commits removed it is from the source
  * Way to select which specific repos you want to include in your local collection
  * See if builds that fail can be fixed through this tool
  * Have specific branch/commits in the .txt files
  * Way to use different python, node versions
    * Or install missing python, node modules
  * Include rom box-arts
  * Use actual rom name instead of repo name
  * Auto-detect forks of pokeyellow
  * Make/Apply IPS Patches
