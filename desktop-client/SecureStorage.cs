using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace AITeamRoom;

/// <summary>
/// Шифрование локальных файлов через Windows DPAPI (привязка к учётной записи Windows).
/// </summary>
internal static class SecureStorage
{
    private static readonly byte[] Entropy = Encoding.UTF8.GetBytes("AITeamRoom.v1.takura");

    public const string ConfigFileName = "config.secure";
    public const string MetaFileName = "install.meta.secure";

    public static void WriteProtected(string path, string plaintext)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        var data = ProtectedData.Protect(
            Encoding.UTF8.GetBytes(plaintext),
            Entropy,
            DataProtectionScope.CurrentUser);
        File.WriteAllBytes(path, data);
    }

    public static string? ReadProtected(string path)
    {
        if (!File.Exists(path))
            return null;
        try
        {
            var data = File.ReadAllBytes(path);
            var plain = ProtectedData.Unprotect(data, Entropy, DataProtectionScope.CurrentUser);
            return Encoding.UTF8.GetString(plain);
        }
        catch
        {
            return null;
        }
    }

    public static void SaveConfig(string installDir, AppConfig config)
    {
        var json = JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true });
        WriteProtected(Path.Combine(installDir, ConfigFileName), json);
    }

    public static AppConfig? LoadConfig(string installDir)
    {
        var securePath = Path.Combine(installDir, ConfigFileName);
        var json = ReadProtected(securePath);
        if (string.IsNullOrWhiteSpace(json))
        {
            var legacy = Path.Combine(installDir, "config.json");
            if (File.Exists(legacy))
            {
                try
                {
                    json = File.ReadAllText(legacy);
                    var cfg = JsonSerializer.Deserialize<AppConfig>(json);
                    if (cfg != null)
                    {
                        SaveConfig(installDir, cfg);
                        try { File.Delete(legacy); } catch { /* ignore */ }
                        return cfg;
                    }
                }
                catch { /* fall through */ }
            }
            return null;
        }
        try
        {
            return JsonSerializer.Deserialize<AppConfig>(json);
        }
        catch
        {
            return null;
        }
    }

    public static void SaveInstallMeta(string installDir, InstallMeta meta)
    {
        var json = JsonSerializer.Serialize(meta, new JsonSerializerOptions { WriteIndented = true });
        WriteProtected(Path.Combine(installDir, MetaFileName), json);
    }

    public static InstallMeta? LoadInstallMeta(string installDir)
    {
        var json = ReadProtected(Path.Combine(installDir, MetaFileName));
        if (string.IsNullOrWhiteSpace(json))
            return null;
        try
        {
            return JsonSerializer.Deserialize<InstallMeta>(json);
        }
        catch
        {
            return null;
        }
    }
}

internal sealed class AppConfig
{
    public string Server { get; set; } = Program.DefaultServer;
    public string Version { get; set; } = "1.1.0";
}

internal sealed class InstallMeta
{
    public string InstallPath { get; set; } = "";
    public string InstalledAt { get; set; } = "";
    public bool DesktopShortcut { get; set; } = true;
    public bool StartMenuShortcut { get; set; } = true;
}
