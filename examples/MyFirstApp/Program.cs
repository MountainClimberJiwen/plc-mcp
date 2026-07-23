using System;
using System.IO;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using System.Text;
using Siemens.Engineering.SW.ExternalSources;
using MyFirstApp.Config;

namespace MyFirstApp
{
    public class PLCProject
    {
        private readonly string _plcName;
        private readonly string _sclCodePath;
        private readonly Device _plcDevice;
        private readonly PlcSoftware _plcSoftware;

        public PLCProject(Device plcDevice, string plcName, string sclCodePath)
        {
            _plcDevice = plcDevice ?? throw new ArgumentNullException(nameof(plcDevice));
            _plcName = plcName ?? throw new ArgumentNullException(nameof(plcName));
            _sclCodePath = sclCodePath ?? throw new ArgumentNullException(nameof(sclCodePath));
            _plcSoftware = InitializePlcSoftware();
        }

        private PlcSoftware InitializePlcSoftware()
        {
            foreach (var item in _plcDevice.DeviceItems)
            {
                try
                {
                    Console.WriteLine($"Checking device item: {item.Name} ({item.TypeIdentifier})");
                    var softwareContainer = item.GetService<SoftwareContainer>();
                    if (softwareContainer?.Software is PlcSoftware plcSoftware)
                    {
                        Console.WriteLine($"Found PLC software in device item: {item.Name}");
                        return plcSoftware;
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to get software from {item.Name}: {ex.Message}");
                }
            }
            throw new InvalidOperationException("Could not find PLC software in any device item");
        }

        public void ImportSclCode()
        {
            try
            {
                Console.WriteLine($"Importing SCL file in dir: {_sclCodePath}");
                
                var dirPath = new FileInfo(_sclCodePath).FullName;
                Console.WriteLine($"dirPath: {dirPath}");
                
                DeleteExistingExternalSource();
                var files = Directory.GetFiles(dirPath, "*.scl");
                foreach (var file in files)
                {
                    Console.WriteLine($"Importing SCL file: {file}");
                    var name = Path.GetFileName(file) + DateTime.Now.ToString("yyyyMMddHHmmss");
                    // _plcSoftware.ExternalSourceGroup.ExternalSources remove the file if it exists
                    // _plcSoftware.ExternalSourceGroup.ExternalSources.Remove(name);
                    var externalSourceService = _plcSoftware.ExternalSourceGroup.ExternalSources.CreateFromFile(name, file);
                    externalSourceService.GenerateBlocksFromSource();
                }
                
                Console.WriteLine("SCL block created successfully!");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to import SCL code: {ex.Message}");
                throw;
            }
        }

        private void DeleteExistingExternalSource()
        {
            var existingSource = _plcSoftware.ExternalSourceGroup.ExternalSources.Find("test");
            if (existingSource != null)
            {
                Console.WriteLine("Deleting existing external source...");
                existingSource.Delete();
            }
        }

        public void CreateSclBlock()
        {
            Console.WriteLine("Creating SCL block...");

            try
            {
                DeleteExistingBlock();
                ImportSclCode();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to create/update block: {ex.Message}");
                throw;
            }
        }

        private void DeleteExistingBlock()
        {
            var existingBlock = _plcSoftware.BlockGroup.Blocks.FirstOrDefault(b => b.Name == "Block_4");
            if (existingBlock != null)
            {
                Console.WriteLine("Deleting existing block...");
                existingBlock.Delete();
            }
        }
    }

    public class TiaPortalProject : IDisposable
    {
        private readonly TiaPortal _tiaPortal;
        private readonly string _plcName;
        private readonly string _sclCodePath;
        private readonly string _projectPath;
        private readonly AppConfig _config;
        private bool _disposed;

        public TiaPortalProject(string plcName, string sclCodePath, AppConfig config)
        {
            _plcName = plcName;
            _sclCodePath = sclCodePath;
            _config = config ?? throw new ArgumentNullException(nameof(config));
            _projectPath = config.ProjectPath;
            _tiaPortal = ConnectToTiaPortal();
        }

        private TiaPortal ConnectToTiaPortal()
        {
            Console.WriteLine("Checking for existing TIA Portal instances...");
            var existingInstances = TiaPortal.GetProcesses();
            
            if (existingInstances.Any())
            {
                Console.WriteLine("Found existing TIA Portal instances. Attempting to connect...");
                try
                {
                    return existingInstances.First().Attach();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to attach to existing instance: {ex.Message}");
                    throw;
                }
            }
            
            Console.WriteLine("No existing instances found. Starting new TIA Portal...");
            return new TiaPortal(TiaPortalMode.WithUserInterface);
        }

        public void ProcessProject()
        {
            Console.WriteLine("TIA Portal instance connected successfully");
            
            try
            {
                var project = GetCurrentProject(_projectPath);
                var plcDevice = FindPlcDevice(project);
                var plcProject = new PLCProject(plcDevice, _plcName, _sclCodePath);
                plcProject.CreateSclBlock();
            }
            catch (Exception ex)
            {
                Console.WriteLine("Operation failed: " + ex.Message);
                throw;
            }
        }

        private Siemens.Engineering.Project GetCurrentProject(string projectPath)
        {
            var project = _tiaPortal.Projects.FirstOrDefault();
            if (project == null)
            {
                throw new InvalidOperationException("No project is currently open in TIA Portal");
            }
            if (project.Path.FullName != projectPath)
            {
                // project.Close();
                // project = _tiaPortal.Projects.FirstOrDefault();
               throw new InvalidOperationException($"No specified project ({projectPath}) is currently open in TIA Portal");
            }
            
            Console.WriteLine($"Found open project: {project.Path}");
            return project;
        }

        private Device FindPlcDevice(Siemens.Engineering.Project project)
        {
            var devices = project.Devices;
            // assign pn with last part of _plcName, split by '/'
            var pn = _plcName.Split('/').Last();
            var plc = devices.FirstOrDefault(d => d.Name == pn);
            
            if (plc == null)
            {
                Console.WriteLine($"Error: Could not find device named '{_plcName}'");
                Console.WriteLine("Available devices:");
                foreach (var device in devices)
                {
                    Console.WriteLine($"- {device.Name} ({device.TypeIdentifier})");
                    if (device.Name == "PLC_1")
                    {
                        Console.WriteLine($"Found PLC device: {device.Name}");
                        return device;
                    }
                }
                throw new InvalidOperationException($"Could not find PLC device with name: {_plcName}");
            }

            Console.WriteLine($"Found PLC device: {plc.Name}");
            return plc;
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _tiaPortal?.Dispose();
                _disposed = true;
            }
        }
    }

    class Program
    {
        static void Main(string[] args)
        {
            try
            {
                // 加载配置
                var config = AppConfig.Load();
                if (config == null)
                {
                    Console.WriteLine("请先配置config.txt文件后再运行程序。");
                    Console.WriteLine($"ProjectPath: {config.ProjectPath}");
                    return;
                }
                

                // 获取命令行参数   
                string sclCodeDirPath = args.Length > 1 ? args[1] : "scl";
                // assign plcName with last part of sclCodeDirPath, split by '/'
                var plcName = sclCodeDirPath.Split('/').Last();
                Console.WriteLine($"PLC Name: {plcName}");
                Console.WriteLine($"SCL Code Path: {sclCodeDirPath}");
                
                using (var tiaPortalProject = new TiaPortalProject(plcName, sclCodeDirPath, config))
                {
                    tiaPortalProject.ProcessProject();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error occurred: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
            }
        }
    }

    // 定义PLC块类型枚举
    public enum PLCBlockType
    {
        OB = 1,
        FB = 2,
        FC = 3,
        DB = 4
    }
}
