# Tiwut Secure Browser

A modern, secure, and feature-rich web browser built from scratch using Python and the PyQt5 framework. This project demonstrates how to create a complete browsing experience with advanced features like tab management, persistent caching, history, bookmarks, and a download manager, all wrapped in a sleek, dark-mode UI.

This browser is also available as part of the **Tiwut Launcher**.

## Features

-   **Modern Dark-Mode UI**: A visually appealing and user-friendly interface with rounded corners and high contrast.
-   **Tabbed Browsing**: Open, close, and manage multiple web pages in a familiar tabbed interface.
-   **Secure by Default**: Automatically attempts to upgrade HTTP connections to secure HTTPS.
-   **Developer Tools**: Right-click any element on a page and select "Inspect Element" to open the powerful Chromium Web Inspector.
-   **Download Manager**: Seamlessly download files from the web. A dialog will prompt for a save location, and a manager window tracks download progress.
-   **History & Bookmarks**:
    -   Automatically saves your browsing history.
    -   Access your history through a dedicated, searchable dialog.
    -   Add, view, and delete bookmarks for quick access to your favorite sites.
-   **Performance Cache Mode**: An optional persistent disk cache that significantly speeds up loading times for frequently visited pages.
-   **Privacy Controls**: Comprehensive settings to manage how the browser handles cookies (allow all, block all, delete on exit).
-   **External URL Handling**: Intelligently opens non-web links (like `mailto:` or `steam:`) in the appropriate desktop application.
-   **Configurable**: All major settings are saved in a simple `config.ini` file for easy customization.

## Installation

This browser is built for Debian-based Linux distributions (like Ubuntu, Mint, etc.) and uses the `apt` package manager for dependencies.

### 1. Install Dependencies

First, open your terminal and update your package lists:

```bash
sudo apt update
