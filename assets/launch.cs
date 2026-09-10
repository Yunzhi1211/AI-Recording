using System;
using System.Diagnostics;
using System.IO;

internal static class IrisLaunch
{
    [STAThread]
    static void Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string app = Path.Combine(root, "05_qt_app.py");
        string venvW = Path.Combine(root, ".venv", "Scripts", "pythonw.exe");
        string venv = Path.Combine(root, ".venv", "Scripts", "python.exe");
        string py = File.Exists(venvW) ? venvW : (File.Exists(venv) ? venv : "pythonw");
        var psi = new ProcessStartInfo
        {
            FileName = py,
            Arguments = "\"" + app + "\"",
            WorkingDirectory = root,
            UseShellExecute = false
        };
        try
        {
            Process.Start(psi);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            Environment.Exit(1);
        }
    }
}
