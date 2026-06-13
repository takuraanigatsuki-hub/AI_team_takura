using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;

namespace AITeamRoom.Installer;

internal static class InstallerTheme
{
    public static readonly Color Bg = Color.FromArgb(10, 11, 16);
    public static readonly Color Surface = Color.FromArgb(18, 20, 28);
    public static readonly Color Surface2 = Color.FromArgb(24, 27, 38);
    public static readonly Color Border = Color.FromArgb(36, 255, 255, 255);
    public static readonly Color Text = Color.FromArgb(242, 243, 247);
    public static readonly Color Muted = Color.FromArgb(148, 150, 168);
    public static readonly Color Accent = Color.FromArgb(139, 92, 246);
    public static readonly Color Accent2 = Color.FromArgb(122, 162, 255);
    public static readonly Color Success = Color.FromArgb(94, 207, 138);
    public static readonly Color Danger = Color.FromArgb(255, 71, 87);

    public static readonly Font FontUi = new("Segoe UI", 9F);
    public static readonly Font FontTitle = new("Segoe UI Semibold", 11F, FontStyle.Bold);
    public static readonly Font FontHead = new("Segoe UI", 20F, FontStyle.Bold);
    public static readonly Font FontSub = new("Segoe UI", 10F);

    public static void EnableDoubleBuffer(Control c)
    {
        typeof(Control).InvokeMember(
            "DoubleBuffered",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance |
            System.Reflection.BindingFlags.SetProperty,
            null,
            c,
            [true]);
    }

    public static GraphicsPath RoundedRect(Rectangle bounds, int radius)
    {
        var path = new GraphicsPath();
        var d = radius * 2;
        if (d > bounds.Width) d = bounds.Width;
        if (d > bounds.Height) d = bounds.Height;
        path.AddArc(bounds.X, bounds.Y, d, d, 180, 90);
        path.AddArc(bounds.Right - d, bounds.Y, d, d, 270, 90);
        path.AddArc(bounds.Right - d, bounds.Bottom - d, d, d, 0, 90);
        path.AddArc(bounds.X, bounds.Bottom - d, d, d, 90, 90);
        path.CloseFigure();
        return path;
    }

    public static void StylePrimaryButton(Button btn)
    {
        btn.FlatStyle = FlatStyle.Flat;
        btn.FlatAppearance.BorderSize = 0;
        btn.BackColor = Accent;
        btn.ForeColor = Color.White;
        btn.Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold);
        btn.Cursor = Cursors.Hand;
    }

    public static void StyleGhostButton(Button btn)
    {
        btn.FlatStyle = FlatStyle.Flat;
        btn.FlatAppearance.BorderColor = Border;
        btn.FlatAppearance.BorderSize = 1;
        btn.BackColor = Surface2;
        btn.ForeColor = Text;
        btn.Cursor = Cursors.Hand;
    }

    public static void StyleTextBox(TextBox tb)
    {
        tb.BackColor = Surface2;
        tb.ForeColor = Text;
        tb.BorderStyle = BorderStyle.FixedSingle;
        tb.Font = FontUi;
    }

    public static void PaintGradientAccent(Graphics g, Rectangle bounds)
    {
        using var brush = new LinearGradientBrush(bounds, Accent, Accent2, LinearGradientMode.Horizontal);
        g.FillRectangle(brush, bounds);
    }

    public static void ApplyFormShadow(Form form)
    {
        try
        {
            const int dwmwaUseImmersiveDarkMode = 20;
            const int dwmwaWindowCornerPreference = 33;
            const int cornerRound = 2;
            var dark = 1;
            DwmSetWindowAttribute(form.Handle, dwmwaUseImmersiveDarkMode, ref dark, sizeof(int));
            DwmSetWindowAttribute(form.Handle, dwmwaWindowCornerPreference, ref cornerRound, sizeof(int));
        }
        catch { /* older Windows */ }
    }

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);
}
