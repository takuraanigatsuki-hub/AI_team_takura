using Microsoft.Web.WebView2.Core;

namespace AITeamRoom;

internal sealed class MainForm : Form
{
    private readonly string _server;
    private readonly Microsoft.Web.WebView2.WinForms.WebView2 _webView;

    public MainForm(string server)
    {
        _server = server.Trim().TrimEnd('/');
        Text = "AI Team Room";
        Width = 1320;
        Height = 860;
        MinimumSize = new Size(960, 640);
        StartPosition = FormStartPosition.CenterScreen;
        Icon = SystemIcons.Application;

        _webView = new Microsoft.Web.WebView2.WinForms.WebView2
        {
            Dock = DockStyle.Fill,
        };
        Controls.Add(_webView);
        Load += OnFormLoad;
    }

    private async void OnFormLoad(object? sender, EventArgs e)
    {
        try
        {
            var env = await CoreWebView2Environment.CreateAsync(
                userDataFolder: Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "AI Team Room", "WebView2"));
            await _webView.EnsureCoreWebView2Async(env);
            var core = _webView.CoreWebView2;
            core.Settings.UserAgent = Program.DesktopUserAgent;
            core.Settings.AreDefaultContextMenusEnabled = true;
            core.Settings.IsStatusBarEnabled = false;
            core.Settings.IsZoomControlEnabled = false;
            core.NewWindowRequested += (_, args) =>
            {
                args.Handled = true;
                try { System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(args.Uri) { UseShellExecute = true }); }
                catch { /* ignore */ }
            };
            core.NavigationStarting += (_, args) =>
            {
                if (args.Uri.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
                    args.Uri.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                    return;
                args.Cancel = true;
            };
            core.Navigate($"{_server}/client");
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Не удалось запустить WebView2.\n\n{ex.Message}\n\nУстановите Microsoft Edge WebView2 Runtime.",
                "AI Team Room",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            Close();
        }
    }
}
