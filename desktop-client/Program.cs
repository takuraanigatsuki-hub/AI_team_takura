using System.Text.Json;
using Microsoft.Win32;

namespace AITeamRoom;

internal static class Program
{
    public const string DefaultServer = "http://80.78.245.66";
    public const string DesktopUserAgent = "AITeamRoomDesktop/1.1 (Windows; Native)";
    public const string AppName = "AI Team Room";
    public const string ExeName = "AI_Team_Room.exe";
    private const string UninstallRegKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\AITeamRoom";

    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();

        var installDir = GetInstallDir();
        if (args.Contains("--uninstall", StringComparer.OrdinalIgnoreCase))
        {
            RunUninstall(installDir);
            return;
        }

        var server = LoadServerUrl(installDir);
        Application.Run(new MainForm(server, installDir));
    }

    static string GetInstallDir()
    {
        return Path.GetDirectoryName(Application.ExecutablePath) ?? AppContext.BaseDirectory;
    }

    static string LoadServerUrl(string installDir)
    {
        var env = Environment.GetEnvironmentVariable("AI_TEAM_SERVER");
        if (!string.IsNullOrWhiteSpace(env))
            return env.Trim().TrimEnd('/');

        var cfg = SecureStorage.LoadConfig(installDir);
        if (cfg != null && !string.IsNullOrWhiteSpace(cfg.Server))
            return cfg.Server.Trim().TrimEnd('/');

        var legacyDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            AppName);
        var legacyFile = Path.Combine(legacyDir, "config.json");
        if (File.Exists(legacyFile))
        {
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(legacyFile));
                if (doc.RootElement.TryGetProperty("server", out var s))
                {
                    var url = s.GetString();
                    if (!string.IsNullOrWhiteSpace(url))
                    {
                        SecureStorage.SaveConfig(installDir, new AppConfig { Server = url.Trim().TrimEnd('/') });
                        return url.Trim().TrimEnd('/');
                    }
                }
            }
            catch { /* default */ }
        }

        SecureStorage.SaveConfig(installDir, new AppConfig { Server = DefaultServer });
        return DefaultServer;
    }

    static void RunUninstall(string installDir)
    {
        var result = MessageBox.Show(
            $"Удалить {AppName} из\n{installDir}?",
            AppName,
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question);
        if (result != DialogResult.Yes)
            return;

        try
        {
            RemoveShortcut(Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                $"{AppName}.lnk"));
            RemoveShortcut(Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                "Programs", $"{AppName}.lnk"));
        }
        catch { /* ignore */ }

        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(UninstallRegKey, writable: true);
            key?.Close();
            Registry.CurrentUser.DeleteSubKeyTree(UninstallRegKey, throwOnMissingSubKey: false);
        }
        catch { /* ignore */ }

        try
        {
            if (Directory.Exists(installDir))
                Directory.Delete(installDir, recursive: true);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Не удалось удалить все файлы:\n{ex.Message}\n\nУдалите папку вручную:\n{installDir}",
                AppName,
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning);
            return;
        }

        MessageBox.Show($"{AppName} удалён.", AppName, MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    static void RemoveShortcut(string path)
    {
        if (File.Exists(path))
            File.Delete(path);
    }
}
