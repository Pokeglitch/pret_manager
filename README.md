# pret manager

This is a tool to help people maintain various [pret disassemblies](https://github.com/pret) and hacks derived from them.

**Currently for Gen 1/2 Only**

## Installation

Please read the [tutorial](tutorial.md) for installation directions

# GUI

To launch the GUI, call the python script with no arguments

`python .\manage.py`

# CLI

To run the CLI, enter the repository in a shell and enter:

`python manage.py <environment> <repositories> <process>`

### Environment

For Windows only, this defines which Linux Environment to use

  * -env, -e
    * One of: `wsl`, `cygwin`, `w64devkit`

If no environment is supplied, it currently defaults to the settings value, which is `wsl` by default.
  * Can be modified in GUI or by editing `data/settings.json`

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

Please see this file for potential [Future Work](FutureWork.md)

## Contribute

Any help towards this project will be much appreciated!  This could be anything from sharing bugs, informing of missing repositories, adding better Tags/Titles/Descriptions/Artwork, or any feature requests!

[Join the Discord Here](https://discord.gg/dvgYzaZcjK)