# pret manager

This is a tool to help people maintain various [pret disassemblies](https://github.com/pret) and hacks derived from them.

**Currently for Gen 1/2 Only**

## Requirements

The follow programs are needed:
  * python (3.7+)
  * git (2.4+)
  * gh (Github CLI)

If Windows, a Linux environment is needed
  * One of: WSL, Cygwin, w64devkit
  * Within Linux environment, see Linux reqs

If Linux:
  * make (& dependencies required to build rgbds & pret disassemblies)


## GUI

To launch the GUI, call the python script with no arguments

`python .\manage.py`

Optionally, the `<environment>` listed below can be supplied to select the Linux Environment

## Usage

To run, enter the repository in a shell and enter:

`python manage.py <environment> <repositories> <process>`

### Environment

For Windows only, this defines which Linux Environment to use

  * -env, -e
    * One of: `wsl`, `cygwin`, `w64devkit`

If no environment is supplied, it currently defaults to `wsl`

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

If no repositories are provided, it will apply the processes on all repositories

### Process

This will dictate what processes will be applied to the managed reopsitories

  * -process, -p
    * The order of processes to apply to the manager repositories

Following this argument can be any of the following (in any order):

  * u
    * Update - Pull (or clone) the managed repositories
  * b
    * Build the managed repositories
  * c
    * Clean the managed repositories

In addition the above, there is also:

  * -build, -b
    * Arguments for the build process (to select specific branch/commit)

If no commands are provided, it will perform the following:
  * Update
  * Clean
  * Build
  * Clean

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
  