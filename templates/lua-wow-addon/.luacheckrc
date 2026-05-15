-- Luacheck configuration for WoW addon development.
std = "lua51"
max_line_length = 120

exclude_files = {
    "Libs/",
}

globals = {
    "ProjectNameDB",
}

read_globals = {
    "LibStub",
    -- WoW API surface; extend as the addon grows.
    "CreateFrame",
    "C_Timer",
    "print",
}
