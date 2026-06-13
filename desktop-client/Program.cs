using System.Text.Json;

namespace AITeamRoom;

internal static class Program
{
    public const string DefaultServer = "http://80.78.245.66";
    public const string DesktopUserAgent = "AITeamRoomDesktop/1.1 (Windows; Native)";

    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        var server = LoadServerUrl();
        Application.Run(new MainForm(server));
    }

    static string LoadServerUrl()
    {
        var env = Environment.GetEnvironmentVariable("AI_TEAM_SERVER");
        if (!string.IsNullOrWhiteSpace(env))
            return env.Trim().TrimEnd('/');

        var cfgDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "AI Team Room");
        var cfgFile = Path.Combine(cfgDir, "config.json");
        if (File.Exists(cfgFile))
        {
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(cfgFile));
                if (doc.RootElement.TryGetProperty("server", out var s))
                {
                    var url = s.GetString();
                    if (!string.IsNullOrWhiteSpace(url))
                        return url.Trim().TrimEnd('/');
                }
            }
            catch { /* default */ }
        }
        return DefaultServer;
    }
}
