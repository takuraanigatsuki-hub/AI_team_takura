using Microsoft.Web.WebView2.Core;

namespace AITeamRoom;

internal sealed class MainForm : Form
{
    private readonly string _server;
    private readonly string _installDir;
    private readonly Microsoft.Web.WebView2.WinForms.WebView2 _webView;
    private readonly TitleBar _titleBar;

    public MainForm(string server, string installDir)
    {
        _server = server.Trim().TrimEnd('/');
        _installDir = installDir;

        Text = "AI Team Room";
        Width = 1320;
        Height = 860;
        MinimumSize = new Size(960, 640);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.None;
        BackColor = AppTheme.Bg;
        Icon = SystemIcons.Application;

        _titleBar = new TitleBar();
        _titleBar.Attach(this);
        _titleBar.RefreshClicked += (_, _) => _webView.CoreWebView2?.Reload();
        _titleBar.SettingsClicked += (_, _) => ShowSettings();

        _webView = new Microsoft.Web.WebView2.WinForms.WebView2
        {
            Dock = DockStyle.Fill,
            DefaultBackgroundColor = AppTheme.Bg,
        };

        Controls.Add(_webView);
        Controls.Add(_titleBar);
        Load += OnFormLoad;
    }

    private void ShowSettings()
    {
        using var dlg = new SettingsForm(_installDir, _server);
        if (dlg.ShowDialog(this) == DialogResult.OK)
        {
            var url = dlg.ServerUrl;
            if (!string.Equals(url, _server, StringComparison.OrdinalIgnoreCase))
            {
                var restart = MessageBox.Show(this,
                    "Для смены сервера нужен перезапуск приложения. Перезапустить сейчас?",
                    "AI Team Room",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);
                if (restart == DialogResult.Yes)
                {
                    Application.Restart();
                }
            }
        }
    }

    private async void OnFormLoad(object? sender, EventArgs e)
    {
        try
        {
            var webViewDir = Path.Combine(_installDir, "WebView2");
            Directory.CreateDirectory(webViewDir);

            var env = await CoreWebView2Environment.CreateAsync(userDataFolder: webViewDir);
            await _webView.EnsureCoreWebView2Async(env);
            var core = _webView.CoreWebView2;
            core.Settings.UserAgent = Program.DesktopUserAgent;
            core.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All);
            core.WebResourceRequested += (_, args) =>
            {
                args.Request.Headers.SetHeader("x-ai-team-client", "desktop");
            };
            core.Settings.AreDefaultContextMenusEnabled = false;
            core.Settings.IsStatusBarEnabled = false;
            core.Settings.IsZoomControlEnabled = false;
            core.NewWindowRequested += (_, args) =>
            {
                args.Handled = true;
                try
                {
                    System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(args.Uri)
                    {
                        UseShellExecute = true,
                    });
                }
                catch { /* ignore */ }
            };
            core.NavigationStarting += (_, args) =>
            {
                if (args.Uri.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
                    args.Uri.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                    return;
                args.Cancel = true;
            };
            core.NavigationCompleted += (_, args) =>
            {
                if (args.IsSuccess)
                    _titleBar.SetSubtitle("AI Team Room · подключено");
            };
            _titleBar.SetSubtitle("AI Team Room · загрузка…");
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
