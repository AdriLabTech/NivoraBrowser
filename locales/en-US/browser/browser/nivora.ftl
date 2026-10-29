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

## The first-run tour (NivoraTutorial.sys.mjs). It is in Spanish on purpose, whatever the language of the interface;
## the names of the interface itself (New Tab, Add to Essentials, Compact Mode, Join 2 Tabs, Settings) stay in English
## because that is how they appear on screen. The guide is the pixel-art character of the Claude Code plugin for Ryoku.

nivora-action-take-tour = Hacer el tutorial

tour-step-of = { $n } de { $total }
tour-next = Siguiente
tour-back = Atrás
tour-skip = Saltar
tour-finish = Terminar

tour-hello-title = ¡Hola! Soy Adri
tour-hello-body = Te enseño Nivora en un minuto. Usa las flechas o los botones y pulsa Esc cuando quieras parar. Puedes repetir el tutorial desde Settings.

tour-tabs-title = Tus pestañas están en el lateral
tour-tabs-body = Todo lo que tienes abierto aparece en esta lista. Haz clic en una pestaña para ir a ella y usa la fila New Tab de arriba para abrir otra.

tour-palette-title = La paleta de comandos
tour-palette-body = Pulsa { $shortcut } para buscar, abrir una web o ejecutar un comando. Prueba a escribir «nivora» para ver los comandos propios de Nivora.

tour-essentials-title = Essentials
tour-essentials-body = Haz clic derecho en una pestaña y elige Add to Essentials para dejarla arriba, a un clic, en todos los espacios.

tour-spaces-title = Espacios
tour-spaces-body = Un espacio es un grupo de pestañas independiente, por ejemplo trabajo y personal. Aquí ves en cuál estás y cambias de uno a otro.

tour-sidebar-title = Barra lateral y modo compacto
tour-sidebar-body = Este botón muestra u oculta la barra lateral. Haz clic derecho en la barra y elige Compact Mode para esconderla hasta que la necesites.

tour-glance-title = Glance
tour-glance-body = Mantén { $key } y haz clic en un enlace para echarle un vistazo en una ventana flotante, sin salir de la página que estás leyendo.

tour-split-title = Vista dividida
tour-split-body = Selecciona dos pestañas con Ctrl+clic, haz clic derecho en una y elige Join 2 Tabs para verlas lado a lado.

tour-library-title = La biblioteca
tour-library-body = Historial, descargas, multimedia, tus espacios y Boosts, todo en un mismo panel.

tour-settings-title = Settings y este tutorial
tour-settings-body = Abre este menú y elige Settings. En Look and Feel hay un botón para repetir el tutorial cuando quieras volver a verlo.

tour-done-title = ¡Eso es todo!
tour-done-body = Pulsa { $shortcut } y escribe «tutorial» cuando me necesites. Disfruta de Nivora.
