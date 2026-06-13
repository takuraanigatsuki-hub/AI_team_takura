using System.Diagnostics;
using System.Net.Http;
using System.Text.Json;

namespace AITeamRoom.Updater;

internal static class Program
{
    private const string DefaultServer = "http://80.78.245.66";

    [STAThread]
    static async Task Main(string[] args)
    {
        var installDir = args.FirstOrDefault(a => !a.StartsWith('-'))
            ?? Path.GetDirectoryName(Application.ExecutablePath)
            ?? AppContext.BaseDirectory;

        var server = Environment.GetEnvironmentVariable("AI_TEAM_SERVER")?.Trim().TrimEnd('/')
            ?? DefaultServer;

        try
        {
            using var http = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
            var json = await http.GetStringAsync($"{server}/api/downloads/desktop/info");
            using var doc = JsonDocument.Parse(json);
            var setup = doc.RootElement.GetProperty("platforms").EnumerateArray()
                .FirstOrDefault(p => p.GetProperty("id").GetString() == "win-setup");
            if (setup.ValueKind == JsonValueKind.Undefined)
                throw new InvalidOperationException("win-setup not found in API response");

            var url = setup.GetProperty("url").GetString();
            if (string.IsNullOrWhiteSpace(url))
                throw new InvalidOperationException("Empty download URL");

            if (!url.StartsWith("http", StringComparison.OrdinalIgnoreCase))
                url = server + url;

            var temp = Path.Combine(Path.GetTempPath(), "AI_Team_Room_Setup_new.exe");
            var bytes = await http.GetByteArrayAsync(url);
            await File.WriteAllBytesAsync(temp, bytes);

            Process.Start(new ProcessStartInfo(temp)
            {
                UseShellExecute = true,
                Arguments = $"/S /D=\"{installDir}\"",
            })?.WaitForExit(300000);

            File.Delete(temp);
        }
        catch (Exception ex)
        {
            if (args.Contains("--silent")) return;
            MessageBox.Show($"Не удалось обновить:\n{ex.Message}", "AI Team Room Updater",
                MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }
}
