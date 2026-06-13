namespace AITeamRoom.Uninstaller;

using AITeamRoom.Installer;

internal sealed class UninstallerForm : Form
{
    public UninstallerForm(string installDir)
    {
        Text = "AI Team Room — удаление";
        ClientSize = new Size(480, 280);
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = InstallerTheme.Bg;
        ForeColor = InstallerTheme.Text;
        Font = InstallerTheme.FontUi;
        InstallerTheme.EnableDoubleBuffer(this);
        InstallerTheme.ApplyFormShadow(this);

        var titleBar = new InstallerTitleBar(this);
        var body = new Label
        {
            Text = $"Удалить AI Team Room?\n\nПапка:\n{installDir}\n\nБудут удалены приложение, updater и ярлыки.",
            Location = new Point(28, 64),
            Size = new Size(424, 120),
            ForeColor = InstallerTheme.Muted,
        };
        var remove = new Button { Text = "Удалить", Width = 120, Height = 38, Location = new Point(228, 210) };
        var cancel = new Button { Text = "Отмена", Width = 100, Height = 38, Location = new Point(332, 210) };
        InstallerTheme.StylePrimaryButton(remove);
        remove.BackColor = InstallerTheme.Danger;
        InstallerTheme.StyleGhostButton(cancel);
        cancel.Click += (_, _) => Close();
        remove.Click += (_, _) =>
        {
            try { InstallCleanup.Run(installDir); }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            MessageBox.Show("AI Team Room удалён.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            Close();
        };
        Controls.Add(titleBar);
        Controls.Add(body);
        Controls.Add(remove);
        Controls.Add(cancel);
    }
}

internal static class InstallCleanup
{
    public static void Run(string installDir)
    {
        RemoveShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "AI Team Room.lnk"));
        RemoveShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu), "Programs", "AI Team Room.lnk"));
        Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\AITeamRoom", false);
        if (Directory.Exists(installDir))
            Directory.Delete(installDir, recursive: true);
    }

    static void RemoveShortcut(string path)
    {
        if (File.Exists(path)) File.Delete(path);
    }
}
