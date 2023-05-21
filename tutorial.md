# Required Software Installation

## Linux

If you are using a Windows machine, you will need a Linux environment to build the repositories.  

The follow are supported:
  * Windows Subsystem for Linux (WSL)
    * https://learn.microsoft.com/en-us/windows/wsl/install
  * Cygwin
    * https://www.cygwin.com/
  * w64devkit
    * https://github.com/skeeto/w64devkit/releases


You will have to [update the settings](#settings) to make sure pret_manager uses the correct environment.


**NOTE:** If you are unfamiliar with Linux, use w64devkit, as that includes everything that you will need.

Otherwise, continue below to see the requirements for the other environments.

### Cygwin Requirements

If using Cygwin, be sure to install the packages necessary to build a repository:
  * make
  * gcc-core

These can be found during installation at the **Select Packages** step, under the **Devel** category

If you have issues building a repository, please see the INSTALL.md file for that repository for help

### WSL or Linux Requirements

If you are using a Linux machine, or WSL, then you will need to be able to compile RGBDS.

The follow packages are necessary:
  * make
  * gcc
  * g++
  * bison
  * pkg-config
  * libpng-dev

These can all be installed in a Linux shell via the folowing command:

`sudo apt-get install make gcc g++ bison pkg-config libpng-dev -y`

See this link for additional instructions if you have issues while building:
  * https://rgbds.gbdev.io/install#building-from-source

## Python

Download and install the latest python if you dont have it or the one is have is earlier than 3.7:
  * https://www.python.org/downloads/

## Git

Download and install the latest git if you dont have it or if the one you have is earlier than 2.4:

  * https://git-scm.com/downloads

## Github CLI

Download and install github CLI if you dont have it, and follow the instructions to atuhenticate with your account:
  * https://cli.github.com/

**Make sure you authenticate the github cli, or it will not be able to download releases:**

Interactively login with:
`gh auth login`

See here for more: https://cli.github.com/manual/gh_auth_login

**Note:** If you have issues with gh crashing, try installing in the Linux environment and changing the settings for `gh` to use the Linux environment

# pret_manager Installation

Using a shell window, navigate to the directory where you would like pret_manager to be installed, and clone it with the following command:

`git clone https://github.com/pokeglitch/pret_manager`

Enter the pret_manager directory with the following command:

`cd pret_manager`


Install the python dependency libraries:

`pip install PyQt5`

Start pret_manager:

`python ./manage.py`

### Settings

Once pret_manager opens, beside to update the following options (if using Windows to match your environment):

  * linux
    * Either WSL, Cygwin, or w64devkit

If using Cygwin or w64devkit, ensure the path for that directory is accurate

The settings will save automatically

## Troubleshooting
If you run into issues executing `pip` or `python`, try some of these solutions:

### pip not found
  * Navigate to the python directory, enter the Scripts folder, and run the `pip` command using a shell inside that folder
  * Otherwise, edit the account Environment Variables to include the python directory in the PATH

### If receiving permission errors:
  * Opening the shell window as Adminstrator

### If `python` opens the Windows Store
  * Try using `py` instead of `python`
  * Otherwise, follow these instructions:
    * https://stackoverflow.com/questions/58754860/cmd-opens-windows-store-when-i-type-python
