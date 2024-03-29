# Future Work

## GUI

### Customization
  * User defined cart colors & labels

### Filter
  * Invert Filter
  * Save / Load Filter
  * Set Default Filter / Utilize Default Filter

### Lists
  * Import a New List
  * Show # of Games in List

### Browser
  * Display # of Games in Browser
  * Tiles Sorting
    * Last Commit Date, Alphabetical, etc

### Game Panel
  * Tabbed Panel Display instead of one at a time
  * Shows lists containing Game
  * Don't show build details for 'extras' repos
  * Don't re-draw the trees on update, only refresh the changed items
  * Show which branches are outdated
  * Add 'Delete' option to all Context Menus
  
## Content
  * Proper Title, Artwork, Tags, Description, and Basis for all Games
  * Make Tags Nestable
    * i.e. Gen1, Gen2, TCG
  * Associate Authors with Teams or Collaborative Projects

## Ease of Use
  * Auto-detect Linux environment
    * Install proper libraries if missing
    * Manage w64devkit repository if no Linux option available

## Source Code
  * General improvement of organiation and consistent paradigm
  * Clean up Parameter handling for subprocess.Popen
  * Safer File Operations
    * Handle reading corrupted files
    * Separate Process
    * Create backups
  * Improve Boot Time
    * Only create objects when necessary
    * Thumbnails

## Processing
  * Fallback Plan when `gh` is available
    * Memoize into data.json and download via http (?)

## Building
  * Extract Make targets
    * Provide option to select which to include
  * Fix repositories that do not build
    * Some require rgbds to be inside the repository (BW3G)
    * Identify and use required versions & libraries for Python, Node, C, Linux packages, etc

## Functionality
  * Handle when a repository changes names
  * Export Game Builds to external Directory
  * Add Local / Custom repositories
  * Download & apply binary patches
  * Download manuals, guides, etc

## CLI
  * `-l` to filter by list
  * `-f` to filter by flag
    * Way to use a Saved Filter
  * `-s` to search
  * Use the same 'filter' function that GUI uses

## More Sophistication
  * Multiple Themese
  * Git GUI (i.e. giggle)
    * Tree view of all forks/sources
      * Identify deriviate count for all games
  * Upgrade to PyQt6
  * File System Watcher to always reflect directory state