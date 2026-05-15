-- ProjectName: addon entry point.
-- Ace3 bootstrap; reference only the Ace3 libraries actually used.
local ProjectName = LibStub("AceAddon-3.0"):NewAddon(
    "ProjectName", "AceConsole-3.0", "AceEvent-3.0")

local defaults = {
    enabled = true,
}

function ProjectName:OnInitialize()
    -- SavedVariables declared in the .toc; initialize on first run.
    ProjectNameDB = ProjectNameDB or defaults
    self.db = ProjectNameDB

    self:RegisterChatCommand("projectname", "OnSlashCommand")
end

function ProjectName:OnEnable()
    self:RegisterEvent("PLAYER_ENTERING_WORLD")
end

function ProjectName:PLAYER_ENTERING_WORLD()
    self:Print("ProjectName loaded.")
end

function ProjectName:OnSlashCommand(input)
    self:Print("ProjectName: " .. (input ~= "" and input or "no arguments"))
end
