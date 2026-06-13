using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;

namespace AITeamRoom;

internal sealed class TitleBar : Panel
{
    public event EventHandler? RefreshClicked;
    public event EventHandler? SettingsClicked;

    private const int WmNcLButtonDown = 0xA1;
    private const int HtCaption = 0x2;

    [DllImport("user32.dll")]
    private static extern bool ReleaseCapture();

    [DllImport("user32.dll")]
    private static extern int SendMessage(IntPtr hWnd, int msg, int wParam, int lParam);

    private readonly Label _title;
    private readonly FlowLayoutPanel _right;
    private Form? _host;

    public TitleBar()
    {
        DoubleBuffered = true;
        Height = 44;
        Dock = DockStyle.Top;
        BackColor = AppTheme.Surface;
        Padding = new Padding(12, 0, 8, 0);

        var left = new Panel
        {
            Dock = DockStyle.Left,
            Width = 220,
            BackColor = Color.Transparent,
        };
        var mark = new Label
        {
            Text = "🤖",
            AutoSize = true,
            Font = new Font("Segoe UI Emoji", 14F),
            ForeColor = AppTheme.Text,
            Location = new Point(0, 8),
        };
        _title = new Label
        {
            Text = "AI Team Room",
            AutoSize = true,
            Font = AppTheme.FontTitle,
            ForeColor = AppTheme.Text,
            Location = new Point(32, 11),
        };
        left.Controls.Add(mark);
        left.Controls.Add(_title);

        _right = new FlowLayoutPanel
        {
            Dock = DockStyle.Right,
            AutoSize = true,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            BackColor = Color.Transparent,
            Padding = new Padding(0, 6, 0, 0),
        };

        _right.Controls.Add(MakeIconButton("⟳", "Обновить", (_, _) => RefreshClicked?.Invoke(this, EventArgs.Empty)));
        _right.Controls.Add(MakeIconButton("⚙", "Настройки", (_, _) => SettingsClicked?.Invoke(this, EventArgs.Empty)));
        _right.Controls.Add(MakeIconButton("—", "Свернуть", (_, _) => MinimizeHost()));
        _right.Controls.Add(MakeIconButton("□", "Развернуть", (_, _) => ToggleMaximize()));
        _right.Controls.Add(MakeIconButton("✕", "Закрыть", (_, _) => CloseHost(), danger: true));

        Controls.Add(_right);
        Controls.Add(left);

        MouseDown += (_, e) => { if (e.Button == MouseButtons.Left) BeginDrag(); };
        left.MouseDown += (_, e) => { if (e.Button == MouseButtons.Left) BeginDrag(); };
        _title.MouseDown += (_, e) => { if (e.Button == MouseButtons.Left) BeginDrag(); };
    }

    private void BeginDrag()
    {
        if (_host == null) return;
        ReleaseCapture();
        SendMessage(_host.Handle, WmNcLButtonDown, HtCaption, 0);
    }

    public void Attach(Form host)
    {
        _host = host;
    }

    public void SetSubtitle(string text)
    {
        _title.Text = string.IsNullOrWhiteSpace(text) ? "AI Team Room" : text;
    }

    private Button MakeIconButton(string glyph, string tip, EventHandler onClick, bool danger = false)
    {
        var btn = new Button
        {
            Text = glyph,
            Width = 36,
            Height = 30,
            FlatStyle = FlatStyle.Flat,
            ForeColor = danger ? AppTheme.Danger : AppTheme.Muted,
            BackColor = Color.Transparent,
            Font = new Font("Segoe UI", 11F),
            Cursor = Cursors.Hand,
            Margin = new Padding(2, 0, 2, 0),
        };
        btn.FlatAppearance.BorderSize = 0;
        btn.FlatAppearance.MouseOverBackColor = Color.FromArgb(32, 255, 255, 255);
        btn.FlatAppearance.MouseDownBackColor = Color.FromArgb(48, 255, 255, 255);
        var tt = new ToolTip();
        tt.SetToolTip(btn, tip);
        btn.Click += onClick;
        return btn;
    }

    private void MinimizeHost() => _host?.WindowState = FormWindowState.Minimized;

    private void ToggleMaximize()
    {
        if (_host == null) return;
        _host.WindowState = _host.WindowState == FormWindowState.Maximized
            ? FormWindowState.Normal
            : FormWindowState.Maximized;
    }

    private void CloseHost() => _host?.Close();

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        using var border = new Pen(AppTheme.Border);
        g.DrawLine(border, 0, Height - 1, Width, Height - 1);
        var accent = new Rectangle(0, Height - 2, Math.Min(120, Width), 2);
        AppTheme.PaintGradientAccent(g, accent);
    }
}
