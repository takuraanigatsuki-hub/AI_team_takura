namespace AITeamRoom.Uninstaller;

internal static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        var dir = args.FirstOrDefault(a => !a.StartsWith('-'))
            ?? Path.GetDirectoryName(Application.ExecutablePath)
            ?? Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        try
        {
            Application.Run(new UninstallerForm(dir));
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "AI Team Room Uninstall", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
