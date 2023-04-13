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

  * -repos, -r
    * Repo(s) to manage
      * In form of <Author>/<Title>
  * -exclude-repos, -xr
    * Repo(s) to not manage
      * In form of <Author>/<Title>
  * -authors, -a
    * Author(s) to manage
  * -exclude-authors, -xa
    * Author(s) to not manage
  * -tags, -t
    * Tag(s) to manage (will exclude all other tags)
  * -exclude-tags, -xt
    * Tags(s) to not manage

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

### **Functionality**
  * Can use specific 'make' commands for each repo
  * Manage pret repos separately (no need to rebuild with new commit)
  * Option to clean and retry for failed builds
    * Option to mark as failed and wont attempt to build again unless unmarked
  * Specific scripts to fix builds for certain repos
    * i.e. pokegold-spaceworld, poketcg2
  * Way to use different python, node versions (and/or install missing)
  * Auto-detect forks of pokeyellow
  * Make/Apply IPS Patches
    * No need to select source, since its already known and the source rom is already built
  * Assign forks as branches of the original source
  
### **Data**

In data.json:
  * Field for hack name (rather than name of the repository)
  * Add tags to all (major, minor, etc)
  * Field for specific commit/branch builds (if not using Github Releases)
  * List of known RGBDS versions that fail/build, and last commit which was tested

JSON config file for user preferences:
  * Default emulator
    * Specific emulator for specific repos/builds
  * Point to own rgbds directory (instead of building in this repo)
  * Which repos to ignore/include, favorites

### **GUI**
  * Update all config file options visually
  * Display status of all repos (perform a fetch at the start)
    * Show how many commits since fork
  * Select specific repositorys for building
    * Can select specific branches/commits
    * Can select specific different rgbds/python/node versions
  * Can select specific 'make' commands
    * Need to parse Makefile
  * Include rom box-arts
  * Launch game in emulator/open repo in VS Code
  * Display README when a game is selected
  