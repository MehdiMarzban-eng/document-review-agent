using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
[assembly: System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8")]

class SetupWindow : Form {
    Label status = new Label();
    ProgressBar progress = new ProgressBar();
    Button install = new Button();
    WebClient client;
    static Dictionary<string,object> config;
    static string home = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DocumentReviewLocal");
    static string folder;
    static string python;
    [STAThread] static void Main() {
        AppContext.SetSwitch("Switch.System.IO.UseLegacyPathHandling", false);
        AppContext.SetSwitch("Switch.System.IO.BlockLongPaths", false);
        string[] args = Environment.GetCommandLineArgs();
        if(args.Length == 4 && args[1] == "--test-extract") {
            try { ExtractPackage(args[2],args[3]); Environment.Exit(0); }
            catch(Exception error) { File.WriteAllText(args[2]+".error",error.ToString()); Environment.Exit(1); }
            return;
        }
        using (var reader = new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("install.json")))
            config = new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
        folder = Path.Combine(home, "app", ((string)config["version"]).Replace("local-preview-", ""));
        python = Path.Combine(folder,"python","pythonw.exe");
        if (File.Exists(Path.Combine(folder,"installed.txt")) && File.Exists(python)) { Launch(); return; }
        Application.EnableVisualStyles();
        var form = new SetupWindow();
        foreach(string argument in Environment.GetCommandLineArgs()) if(argument.StartsWith("--smoke-capture=")) {
            string capture=argument.Substring("--smoke-capture=".Length);
            var timer=new System.Windows.Forms.Timer(); timer.Interval=800;
            timer.Tick+=(s,e)=>{timer.Stop();using(var image=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(image,new Rectangle(0,0,form.Width,form.Height));image.Save(capture);}form.Close();};
            timer.Start();
        }
        Application.Run(form);
    }
    public SetupWindow() {
        Text="Document Review Agent"; ClientSize=new Size(500,270); StartPosition=FormStartPosition.CenterScreen;
        FormBorderStyle=FormBorderStyle.FixedDialog; MaximizeBox=false;
        BackColor=Color.FromArgb(246,248,252); Font=new Font("Segoe UI",11);
        var title = new Label {Text="Local edition setup",Left=28,Top=25,Width=440,Height=35,Font=new Font("Segoe UI",18,FontStyle.Bold)};
        status.SetBounds(28,75,440,70); status.Text="Download: about 6.6 GB. Free space: 14 GB.\nApp 400 MB · Ollama 1.47 GB · Qwen 4.7 GB.";
        progress.SetBounds(28,160,440,15);
        install.SetBounds(28,195,140,40); install.Text="Install"; install.Click += async (s,e)=>await Install();
        Controls.AddRange(new Control[]{title,status,progress,install});
        FormClosing += (s,e)=>{if(client!=null) client.CancelAsync();};
    }
    async Task Install() {
        install.Enabled=false;
        string archive=Path.Combine(home,"app-download.zip");
        try {
            Directory.CreateDirectory(home);
            ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
            client=new WebClient();
            client.DownloadProgressChanged+=(s,e)=>{progress.Value=e.ProgressPercentage;status.Text="Downloading app dependencies: "+e.ProgressPercentage+"%";};
            await client.DownloadFileTaskAsync(new Uri((string)config["url"]),archive);
            status.Text="Installing..."; progress.Style=ProgressBarStyle.Marquee;
            await Task.Run(()=> {
                string hash;
                using(var sha=SHA256.Create()) using(var source=File.OpenRead(archive))
                    hash=BitConverter.ToString(sha.ComputeHash(source)).Replace("-","").ToLowerInvariant();
                if(hash!=(string)config["sha256"]) throw new Exception("Download verification failed. Please retry.");
                ExtractPackage(archive,folder);
                File.WriteAllText(Path.Combine(folder,"installed.txt"),(string)config["sha256"]);
            });
            File.Delete(archive);
            string savedExe=Path.Combine(home,"Document Review Agent.exe");
            string current=Assembly.GetExecutingAssembly().Location;
            if(!string.Equals(current,savedExe,StringComparison.OrdinalIgnoreCase)) File.Copy(current,savedExe,true);
            try {
                dynamic shell=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
                dynamic shortcut=shell.CreateShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Document Review Agent.lnk"));
                shortcut.TargetPath=savedExe; shortcut.WorkingDirectory=home; shortcut.Save();
            } catch { /* A locked-down desktop must not prevent installation. */ }
            Launch(); Close();
        } catch(Exception error) {status.Text=error is PathTooLongException ? "The install path is too long. Download the latest installer." : error.Message;progress.Style=ProgressBarStyle.Blocks;install.Text="Retry";install.Enabled=true;}
    }
    static string LongPath(string path) {
        return path.StartsWith(@"\\") ? @"\\?\UNC\"+path.Substring(2) : @"\\?\"+path;
    }
    static void ExtractPackage(string archive,string destination) {
        string root=Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
        const string prefix="Document Review Local/";
        Directory.CreateDirectory(LongPath(root));
        using(var zip=ZipFile.OpenRead(archive)) foreach(var entry in zip.Entries) {
            string name=entry.FullName.Replace('\\','/');
            if(!name.StartsWith(prefix,StringComparison.Ordinal)) throw new Exception("Invalid archive root.");
            string relative=name.Substring(prefix.Length);
            if(relative.Length==0) continue;
            // Reject rooted paths, alternate data streams and traversal before using extended paths.
            if(relative.Contains(":") || relative.StartsWith("/") || Array.Exists(relative.Split('/'),p=>p==".."))
                throw new Exception("Invalid archive path.");
            string target=Path.GetFullPath(Path.Combine(root,relative));
            if(!target.StartsWith(root,StringComparison.OrdinalIgnoreCase)) throw new Exception("Invalid archive path.");
            if(name.EndsWith("/")) {Directory.CreateDirectory(LongPath(target));continue;}
            Directory.CreateDirectory(LongPath(Path.GetDirectoryName(target)));
            entry.ExtractToFile(LongPath(target),true);
        }
    }
    static void Launch() {
        Process.Start(new ProcessStartInfo(python,"-I \""+Path.Combine(folder,"launcher.py")+"\"") {
            WorkingDirectory=folder,UseShellExecute=false,CreateNoWindow=true});
    }
}
