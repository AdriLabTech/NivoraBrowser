# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

## Nivora command palette and central settings.

nivora-dialog-title = Nivora

nivora-action-new-tab = New Tab
nivora-action-open-history = Open History
nivora-action-open-downloads = Open Downloads
nivora-action-search-open-tabs = Search Open Tabs
nivora-action-close-duplicate-tabs = Close Duplicate Tabs
nivora-action-toggle-animations = Toggle Animations
nivora-action-export-settings = Export Nivora Settings
nivora-action-import-settings = Import Nivora Settings
nivora-action-reset-settings = Reset Nivora Settings to Defaults

nivora-confirm-close-duplicates =
    Close { $count ->
        [one] 1 duplicate tab
       *[other] { $count } duplicate tabs
    }? One tab of each page stays open. Pinned and essential tabs are never closed.

nivora-confirm-reset-settings = Reset every setting Nivora manages to its default? Your bookmarks, history and passwords are not affected.

nivora-settings-export-title = Export Nivora settings
nivora-settings-export-done =
    Saved { $count ->
        [one] 1 setting
       *[other] { $count } settings
    }. The file contains no passwords, cookies or other secrets.
nivora-settings-export-failed = The settings could not be saved.

nivora-settings-import-title = Import Nivora settings
nivora-settings-import-confirm =
    Apply { $count ->
        [one] 1 setting
       *[other] { $count } settings
    } from this file? They replace your current values for those settings.
nivora-settings-import-nothing = The file does not contain any setting to apply.
nivora-settings-import-too-large = This file is too large to be a Nivora settings file.
nivora-settings-import-unreadable = The file could not be read.
nivora-settings-import-invalid = This file cannot be imported, and nothing was changed:{ $reasons }
nivora-settings-import-done =
    Applied { $count ->
        [one] 1 setting
       *[other] { $count } settings
    }.

nivora-settings-reset-done =
    Reset { $count ->
        [one] 1 setting
       *[other] { $count } settings
    } to the default.
