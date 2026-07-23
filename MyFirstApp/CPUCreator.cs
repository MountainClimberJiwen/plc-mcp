// using System;
// using System.Linq;
// using Siemens.Engineering;
// using Siemens.Engineering.HW;
// using Siemens.Engineering.HW.Features;

// namespace MyFirstApp
// {
//     public class CPUCreator
//     {
//         private readonly TiaPortal _tiaPortal;
//         private readonly string _projectPath;

//         public CPUCreator(TiaPortal tiaPortal, string projectPath)
//         {
//             _tiaPortal = tiaPortal ?? throw new ArgumentNullException(nameof(tiaPortal));
//             _projectPath = projectPath ?? throw new ArgumentNullException(nameof(projectPath));
//         }

//         public void CreateCPU1513()
//         {
//             try
//             {
//                 var project = GetProject();
//                 Console.WriteLine("Project opened successfully.");

//                 // Create a new device
//                 var hwConfiguration = project.DeviceGroups.First();
//                 var deviceItemComposition = hwConfiguration.Devices;

//                 // Check if device already exists
//                 if (deviceItemComposition.Any(d => d.Name == "PLC_1"))
//                 {
//                     Console.WriteLine("Device 'PLC_1' already exists. Skipping creation.");
//                     return;
//                 }

//                 // Create new device (1513 CPU)
//                 var typeIdentifier = "6ES7 513-1AL02-0AB0"; // 1513-1 PN CPU
//                 Console.WriteLine($"Creating new device with TypeIdentifier: {typeIdentifier}");
//                 var device = deviceItemComposition.CreateWithItem(typeIdentifier, "PLC_1", "PLC_1");
                
//                 // Configure IP address if needed
//                 ConfigureIPAddress(device);

//                 Console.WriteLine("CPU 1513 created successfully!");
//             }
//             catch (Exception ex)
//             {
//                 Console.WriteLine($"Error creating CPU: {ex.Message}");
//                 throw;
//             }
//         }

//         private Project GetProject()
//         {
//             var project = _tiaPortal.Projects.FirstOrDefault();
//             if (project == null)
//             {
//                 throw new InvalidOperationException("No project is currently open in TIA Portal");
//             }
//             if (project.Path.FullName != _projectPath)
//             {
//                 throw new InvalidOperationException($"Project at path {_projectPath} is not currently open in TIA Portal");
//             }
//             return project;
//         }

//         private void ConfigureIPAddress(Device device)
//         {
//             try
//             {
//                 // Get the Ethernet interface
//                 var networkInterface = device.DeviceItems
//                     .First(di => di.Classification == DeviceItemClassification.HM)
//                     .DeviceItems
//                     .First(di => di.Name.Contains("PROFINET interface"));

//                 // Get the Ethernet port
//                 var networkPort = networkInterface.DeviceItems
//                     .First(di => di.Classification == DeviceItemClassification.Port);

//                 // Configure IP address
//                 var addresses = networkInterface.GetAttribute("Addresses");
//                 if (addresses != null)
//                 {
//                     addresses.SetAttribute("IPAddress", "192.168.0.1");
//                     addresses.SetAttribute("SubnetMask", "255.255.255.0");
//                 }

//                 Console.WriteLine("IP address configured successfully.");
//             }
//             catch (Exception ex)
//             {
//                 Console.WriteLine($"Warning: Could not configure IP address: {ex.Message}");
//                 // Continue execution as IP configuration is optional
//             }
//         }
//     }
// } 