Download and install the latest python if you dont have it or the one is have is earlier than 3.7
https://www.python.org/downloads/

Download and install the latest git if you dont have it or if the one you have is earlier than 2.4
https://git-scm.com/downloads

Download and install github CLI if you dont have it, and follow the instructions to atuhenticate with your account (This is used to download releases)
https://cli.github.com/

**Make sure you authenticate the github cli, or it will not be able to download releases.**

Interactively login with:
`gh auth login`

See here for more: https://cli.github.com/manual/gh_auth_login

**NOTE: gh will NOT work if working on separate drives**


git clone the pret-manager repository:
`git clone https://github.com/pokeglitch/pret_manager`

Install dependencies for rgbds:
https://rgbds.gbdev.io/install#2-build

`wsl sudo apt-get install make gcc g++ bison pkg-config libpng-dev -y`

Enter the pret_manager directory.

Install python ilbraries:
`pip install PyQt5`

edit account environment variables
in python diretory, enter Scripts folder

in taht folder, run the pip commands

if python opens the windows store, type `py`, else:
https://stackoverflow.com/questions/58754860/cmd-opens-windows-store-when-i-type-python