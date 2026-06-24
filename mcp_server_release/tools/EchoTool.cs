using ModelContextProtocol.Server;
using System.ComponentModel;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.HW.Utilities;
using Siemens.Engineering.SW;
using System.IO;
using Siemens.Engineering.SW.Types;
using Siemens.Engineering.SW.Tags;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.Compiler;
using System.Threading;
using System.Threading.Tasks;
using System;
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using System.IO;
using Siemens.Engineering.SW;
using Siemens.Engineering.Connection;
using Serilog;

namespace TestServerWithHosting.Tools
{
    [McpServerToolType]
    public sealed class EchoTool
    {
        [McpServerTool, Description("Add a new device to the project， the deviceType can either be IO or PLC")]
        public static string AddDevice(Project project, string deviceName, string deviceType)
        {
            if (deviceType == "IO")
            {
                string ioArticle = "GSD:GSDML-V2.32-SIEMENS-SINAMICS_V90-20190415.XML/DAP/IDD_V90PN-V4.7"; // IO Device 料号
                var device = project.Devices.Find(deviceName);
                if (device == null)
                {
                    device = project.Devices.CreateWithItem(ioArticle, deviceName, deviceName);
                } 

            } else if (deviceType == "PLC")
            {
                // 创建CPU设备
                string cpuMlfb = "OrderNumber:6ES7 513-1AL02-0AB0/V2.6"; // CPU 1513-1 PN
                var cpu = project.Devices.Find(deviceName);
                if (cpu == null)
                {
                    cpu = project.Devices.CreateWithItem(cpuMlfb, deviceName, deviceName);
                }
            }
            return "Device " + deviceName + " added to project ";
        }


        [McpServerTool, Description("Add a new network to the project")]
        public static string AddNetwork(Project project, string networkName)
        {
            // var request = new NetworkRequest { NetworkName = networkName };
            SubnetComposition subnets = project.Subnets;
            var subnet = subnets.Find(networkName);
      
            if (subnet == null)
            {
                subnet = subnets.Create("System:Subnet.ProfidriveIntegrated", networkName);
            }

            return "network " + networkName + " added to project ";
        }

        [McpServerTool, Description("Add a new network to the project")]
        public static string AddDeviceToNetwork(Project project, string networkName, string deviceName, string ip, 
        string subnetMask)
        {
            // var request = new NetworkRequest { NetworkName = networkName };
            try
            {
                SubnetComposition subnets = project.Subnets;
                var subnet = subnets.Find(networkName);
                var device = project.Devices.Find(deviceName);
                var networkInterface = device.DeviceItems[1].DeviceItems
                    .First(di => di.Name.Contains("PN-IO"));
                var networkProvider = networkInterface.GetService<NetworkInterface>();
                if (networkProvider != null)
                {
                    var node = networkProvider.Nodes[0];
                    node.SetAttribute("Address", ip);
                    node.SetAttribute("SubnetMask", subnetMask);

                    node.ConnectToSubnet(subnet);
                    Log.Information("PN-IO接口配置成功");
                }
            }
            catch (Exception ex)
            {
                Log.Error($"配置PROFINET接口失败: {ex.Message}");
                Log.Error(ex.StackTrace);
                return "device " + deviceName + " failed to add to network " + networkName;
            } 
            return "device " + deviceName + " successed to add to network " + networkName;
        }
    }
}