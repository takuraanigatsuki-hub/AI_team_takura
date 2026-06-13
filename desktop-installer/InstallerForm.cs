namespace AITeamRoom.Installer;

internal sealed class InstallerForm : Form
{
    private int _step;
    private readonly StepRail _rail = new();
    private readonly Panel _body = new() { Dock = DockStyle.Fill, Padding = new Padding(28, 12, 28, 8) };
    private readonly Panel _scrollHost = new() { Dock = DockStyle.Fill, AutoScroll = true };
    private readonly Panel _content = new()
    {
        Dock = DockStyle.Top,
        AutoSize = true,
        AutoSizeMode = AutoSizeMode.GrowAndShrink,
        MinimumSize = new Size(540, 220),
    };
    private readonly Panel _footer = new() { Dock = DockStyle.Bottom, Height = 68, Padding = new Padding(24, 14, 24, 14) };
    private readonly Button _back = new() { Text = "Назад", Width = 100, Height = 38 };
    private readonly Button _next = new() { Text = "Далее", Width = 132, Height = 38 };
    private readonly GradientProgressBar _progress = new() { Visible = false, Margin = new Padding(28, 0, 28, 6) };
    private readonly Label _status = new()
    {
        AutoSize = false,
        Height = 22,
        Visible = false,
        ForeColor = InstallerTheme.Muted,
        TextAlign = ContentAlignment.MiddleLeft,
        Dock = DockStyle.Top,
        Padding = new Padding(28, 0, 28, 4),
    };

    private TextBox _pathBox = null!;
    private CheckBox _chkDesktop = null!;
    private CheckBox _chkMenu = null!;
    private CheckBox _chkLaunch = null!;
    private string _installPath = InstallEngine.DefaultInstallPath;
    private bool _installOk;
    private bool _transitioning;

    public InstallerForm()
    {
        Text = "AI Team Room — установка";
        ClientSize = new Size(620, 520);
        FormBorderStyle = FormBorderStyle.None;
        MaximizeBox = false;
        MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = InstallerTheme.Bg;
        ForeColor = InstallerTheme.Text;
        Font = InstallerTheme.FontUi;
        InstallerTheme.EnableDoubleBuffer(this);

        var titleBar = new InstallerTitleBar(this);

        InstallerTheme.StyleGhostButton(_back);
        InstallerTheme.StylePrimaryButton(_next);
        _back.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        _next.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        _back.Location = new Point(360, 14);
        _next.Location = new Point(468, 14);
        _back.Click += (_, _) => { if (_step > 0 && !_transitioning) _ = GoToStepAsync(_step - 1); };
        _next.Click += (_, _) => OnNext();

        _footer.Controls.Add(_back);
        _footer.Controls.Add(_next);
        _footer.BackColor = InstallerTheme.Surface;
        _footer.Paint += (_, e) =>
        {
            using var pen = new Pen(InstallerTheme.Border, 1f);
            e.Graphics.DrawLine(pen, 0, 0, _footer.Width, 0);
        };

        _scrollHost.Controls.Add(_content);
        _body.Controls.Add(_scrollHost);

        Controls.Add(_body);
        Controls.Add(_status);
        Controls.Add(_progress);
        Controls.Add(_footer);
        Controls.Add(_rail);
        Controls.Add(titleBar);

        Load += (_, _) => InstallerTheme.ApplyFormShadow(this);
        Shown += async (_, _) => await GoToStepAsync(0, instant: true);
    }

    async Task GoToStepAsync(int step, bool instant = false)
    {
        if (_transitioning || step == _step && !instant) return;
        _transitioning = true;
        _next.Enabled = false;
        _back.Enabled = false;

        if (!instant)
        {
            for (var i = 0; i < 8; i++)
            {
                _content.Top = -i * 3;
                await Task.Delay(18);
            }
        }

        _step = step;
        _rail.AnimateTo(step);
        RebuildStep();
        UpdateChrome();

        _content.Top = instant ? 0 : 24;
        if (!instant)
        {
            for (var i = 8; i >= 0; i--)
            {
                _content.Top = i * 3;
                await Task.Delay(16);
            }
        }
        _content.Top = 0;

        _transitioning = false;
        UpdateChrome();
    }

    void UpdateChrome()
    {
        _progress.Visible = _step == 2;
        _status.Visible = _step == 2;
        _back.Enabled = _step is 1 && !_transitioning;
        _next.Enabled = _step != 2 && !_transitioning;
        _next.Text = _step switch
        {
            0 => "Начать →",
            1 => "Установить",
            3 when _installOk => "Запустить",
            3 => "Закрыть",
            _ => "Далее",
        };
        if (_step == 3 && !_installOk)
            _next.Text = "Закрыть";
    }

    void RebuildStep()
    {
        _content.Controls.Clear();
        switch (_step)
        {
            case 0: BuildWelcome(); break;
            case 1: BuildPath(); break;
            case 2: BuildProgress(); break;
            case 3: BuildDone(); break;
        }
        _content.PerformLayout();
    }

    void BuildWelcome()
    {
        var hero = new HeroPanel { Emoji = "🤖", Title = "Добро пожаловать" };
        var intro = MakeMuted(
            "Установите нативный клиент AI Team Room — рабочая область с 3D-студией, Kanban и чатом с 13 агентами.");
        var features = new FeatureList();
        features.SetItems([
            "Подключение к серверу takura",
            "Splash, вход через браузер, handoff",
            "Конфигурация шифруется (Windows DPAPI)",
            "Ярлыки на рабочем столе и в меню Пуск",
        ]);
        _content.Controls.Add(features);
        _content.Controls.Add(intro);
        _content.Controls.Add(hero);
    }

    void BuildPath()
    {
        AddHead("Папка установки");
        AddMuted("Выберите каталог. Конфигурация будет сохранена в зашифрованных файлах рядом с приложением.");

        var pathRow = new Panel
        {
            Height = 36,
            Dock = DockStyle.Top,
            Margin = new Padding(0, 12, 0, 0),
        };

        _pathBox = new TextBox
        {
            Text = _installPath,
            Dock = DockStyle.Fill,
            Margin = new Padding(0, 0, 96, 0),
        };
        InstallerTheme.StyleTextBox(_pathBox);

        var browse = new Button
        {
            Text = "Обзор…",
            Dock = DockStyle.Right,
            Width = 88,
        };
        InstallerTheme.StyleGhostButton(browse);
        browse.Click += (_, _) => BrowseFolder();

        pathRow.Controls.Add(_pathBox);
        pathRow.Controls.Add(browse);

        var opts = new Panel { Dock = DockStyle.Top, Height = 72, Padding = new Padding(0, 12, 0, 0) };
        _chkDesktop = MakeCheck("Ярлык на рабочем столе", true, 0);
        _chkMenu = MakeCheck("Ярлык в меню Пуск", true, 28);
        opts.Controls.Add(_chkMenu);
        opts.Controls.Add(_chkDesktop);

        _content.Controls.Add(opts);
        _content.Controls.Add(pathRow);
    }

    void BuildProgress()
    {
        AddHead("Установка…");
        AddMuted("Копирование файлов и шифрование конфигурации. Не закрывайте окно.");
        _progress.Value = 0;
        _status.Text = "Старт…";
    }

    void BuildDone()
    {
        var badge = new SuccessBadge
        {
            Failed = !_installOk,
            Location = new Point(0, 0),
            Margin = new Padding(0, 0, 0, 8),
        };
        badge.Play();

        var wrap = new Panel { Height = 80, Dock = DockStyle.Top };
        wrap.Controls.Add(badge);

        AddHead(_installOk ? "Готово!" : "Не удалось установить");
        AddMuted(_installOk
            ? $"Приложение установлено:\n{_installPath}\n\nconfig.secure и install.meta.secure зашифрованы для вашей учётной записи Windows."
            : "Выберите другую папку или проверьте права на запись. Нажмите «Назад» на предыдущем шаге и попробуйте снова.");

        if (_installOk)
        {
            _chkLaunch = MakeCheck("Запустить AI Team Room после закрытия", true, 0);
            var launchPanel = new Panel { Dock = DockStyle.Top, Height = 36, Padding = new Padding(0, 8, 0, 0) };
            launchPanel.Controls.Add(_chkLaunch);
            _content.Controls.Add(launchPanel);
        }

        _content.Controls.Add(wrap);
    }

    void BrowseFolder()
    {
        using var dlg = new FolderBrowserDialog
        {
            Description = "Папка для AI Team Room",
            UseDescriptionForTitle = true,
            SelectedPath = Directory.Exists(_pathBox.Text)
                ? _pathBox.Text
                : InstallEngine.DefaultInstallPath,
        };
        if (dlg.ShowDialog(this) == DialogResult.OK)
            _pathBox.Text = Path.Combine(dlg.SelectedPath, InstallEngine.AppName);
    }

    async void OnNext()
    {
        if (_transitioning) return;

        if (_step == 0)
        {
            await GoToStepAsync(1);
            return;
        }

        if (_step == 1)
        {
            _installPath = _pathBox.Text.Trim();
            if (string.IsNullOrWhiteSpace(_installPath))
            {
                ShowToast("Укажите папку установки.");
                return;
            }

            try
            {
                _installPath = Path.GetFullPath(_installPath);
                Directory.CreateDirectory(_installPath);
            }
            catch (Exception ex)
            {
                ShowToast($"Недоступная папка: {ex.Message}");
                return;
            }

            await GoToStepAsync(2);
            await RunInstallAsync();
            return;
        }

        if (_step == 3)
        {
            if (_installOk && _chkLaunch?.Checked == true)
                LaunchApp();
            Close();
        }
    }

    async Task RunInstallAsync()
    {
        _next.Enabled = false;
        _back.Enabled = false;
        var progress = new Progress<(int pct, string msg)>(p =>
        {
            if (IsDisposed) return;
            _progress.Value = Math.Clamp(p.pct, 0, 100);
            _status.Text = p.msg;
        });

        try
        {
            await InstallEngine.InstallAsync(
                _installPath,
                _chkDesktop.Checked,
                _chkMenu.Checked,
                progress,
                CancellationToken.None);
            _installOk = true;
        }
        catch (Exception ex)
        {
            _installOk = false;
            _status.Text = ex.Message;
            ShowToast(ex.Message);
        }

        await GoToStepAsync(3);
    }

    void LaunchApp()
    {
        var exe = Path.Combine(_installPath, InstallEngine.ExeName);
        if (!File.Exists(exe)) return;
        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(exe)
            {
                UseShellExecute = true,
                WorkingDirectory = _installPath,
            });
        }
        catch { /* ignore */ }
    }

    void ShowToast(string message)
    {
        MessageBox.Show(this, message, Text, MessageBoxButtons.OK,
            MessageBoxIcon.Information);
    }

    CheckBox MakeCheck(string text, bool check, int top)
    {
        return new CheckBox
        {
            Text = text,
            Checked = check,
            Location = new Point(0, top),
            AutoSize = true,
            ForeColor = InstallerTheme.Text,
            Dock = DockStyle.Top,
        };
    }

    void AddHead(string text)
    {
        _content.Controls.Add(new Label
        {
            Text = text,
            Font = InstallerTheme.FontHead,
            ForeColor = InstallerTheme.Text,
            AutoSize = true,
            Dock = DockStyle.Top,
            Margin = new Padding(0, 0, 0, 4),
        });
    }

    Label MakeMuted(string text) => new()
    {
        Text = text,
        ForeColor = InstallerTheme.Muted,
        Font = InstallerTheme.FontUi,
        MaximumSize = new Size(540, 0),
        AutoSize = true,
        Dock = DockStyle.Top,
        Margin = new Padding(0, 0, 0, 8),
    };

    void AddMuted(string text) => _content.Controls.Add(MakeMuted(text));
}
