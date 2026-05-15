# Libs

Third-party libraries are not vendored. The BigWigsMods packager resolves the
externals declared in `.pkgmeta` at package time.

For local play-testing, copy these into this directory (load order is defined
in `embeds.xml`): LibStub, CallbackHandler-1.0, and the Ace3 modules used
(AceAddon-3.0, AceConsole-3.0, AceEvent-3.0). Source: https://www.wowace.com/projects/ace3
