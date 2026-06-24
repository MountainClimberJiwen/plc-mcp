import clr
clr.AddReference('E:\\Program Files\\Siemens\\Automation\\Portal V19\\Bin\\PublicAPI\\Siemens.Engineering.dll')
from System.IO import DirectoryInfo, FileInfo
import Siemens.Engineering as tia
import Siemens.Engineering.HW.Features as hwf
import Siemens.Engineering.Compiler as comp
import os
from System import IO


# 
# # Starting TIA and creating project
# 

# Alternative code to connect to an allready running instance (uncomment to use)

processes = tia.TiaPortal.GetProcesses() # Making a list of all running processes
print (processes)
if len(processes) > 0:
    process = processes[0]                   # Just taking the first process as an example
    mytia = process.Attach()
    myproject = mytia.Projects[0]
    if myproject is not None:
        print("TIA project opened already")
    else:
        print("No TIA project found")
else:

    print("No TIA processes found")
        
    # #Starting TIA with UI, also possible to start without ui
    # print ('Starting TIA with UI')
    # mytia = tia.TiaPortal(tia.TiaPortalMode.WithUserInterface)    
    # project_path = DirectoryInfo ('E:\\TIA_Projects\\test3')
    # project_name = 'SimpleCounter2'
    # # open the project
    # # project = tia.Projects.Open(IO.FileInfo(project_path))
    # # E:\TIA_Projects\test3\SimpleCounter2
    # project_path = "E:\\TIA_Projects\\test3\\SimpleCounter2\\SimpleCounter2.ap19"
    # myproject = mytia.Projects.Open(IO.FileInfo(project_path))

# Creating a new project. Using try/except in case project allready exists


# try:
#     myproject = mytia.Projects.Create(project_path, project_name)
# except Exception as e:
#     print (e)

#
# # Adding HW to the project
#


#Adding the main components

# # print ('Creating PLC1')
# PLC1_mlfb = 'OrderNumber:6ES7 513-1AL02-0AB0/V2.6'
# # init existing PLC1 with mlfb
# # PLC1 = myproject.Devices.CreateWithItem(PLC1_mlfb, 'PLC1', 'PLC1')
# PLC1 = myproject.Devices.Find('PLC1')


# print ('Creating IOnode1')
# IOnode1_mlfb = 'OrderNumber:6ES7 155-6AU01-0BN0/V4.1'
# IOnode1 = myproject.Devices.CreateWithItem(IOnode1_mlfb, 'IOnode1', 'IOnode1')


# print ('Creating HMI1')
# HMI1_mlfb = 'OrderNumber:6AV2 124-0GC01-0AX0/15.1.0.0'
# HMI1 = myproject.Devices.CreateWithItem(HMI1_mlfb, 'HM1', None)

#ToDo Add start screen to avoid compilation error fo the HMI



# Adding IO cards to the PLC and IO station
# This is basic to show how it works, use loops with checks (CanPlugNew) to see if the slot is available
# CanPlugnew is not mandatory, but usefull in real code

# if (PLC1.DeviceItems[0].CanPlugNew('OrderNumber:6ES7 521-1BL00-0AB0/V2.1','IO1',2)): 
#     PLC1.DeviceItems[0].PlugNew('OrderNumber:6ES7 521-1BL00-0AB0/V2.1','IO1', 2)

    
# if (IOnode1.DeviceItems[0].CanPlugNew('OrderNumber:6ES7 131-6BH01-0BA0/V0.0','IO1',1)):
#     IOnode1.DeviceItems[0].PlugNew('OrderNumber:6ES7 131-6BH01-0BA0/V0.0','IO1', 1)



#
# # Creating network, iosytem and setting IP adresses
# 


#creating a list of all found network interfaces on all stations in the station list
n_interfaces = []
# for device in myproject.Devices:
#     device_item_aggregation = device.DeviceItems[1].DeviceItems
#     for deviceitem in device_item_aggregation:
#         network_service = tia.IEngineeringServiceProvider(deviceitem).GetService[hwf.NetworkInterface]()
#         if type(network_service) is hwf.NetworkInterface:
#             n_interfaces.append(network_service)




# Assigning an IP to each item in the list (dirty code, but to demonstrate how theAPI works)

# n_interfaces[0].Nodes[0].SetAttribute('Address','192.168.0.130')
# n_interfaces[1].Nodes[0].SetAttribute('Address','192.168.0.131')
# n_interfaces[2].Nodes[0].SetAttribute('Address','192.168.0.132')



# Creating subnet and IO system on the first item in the list
# # Connects to subnet for remaining devices, if IO device it gets assigned to the IO system
# for n in n_interfaces:
#     if n_interfaces.index(n) == 0:
#         subnet = n_interfaces[0].Nodes[0].CreateAndConnectToSubnet("Profinet")
#         ioSystem = n_interfaces[0].IoControllers[0].CreateIoSystem("PNIO");
#     else:
#         n_interfaces[n_interfaces.index(n)].Nodes[0].ConnectToSubnet(subnet)
#         if (n_interfaces[n_interfaces.index(n)].IoConnectors.Count) >> 0:
#             n_interfaces[n_interfaces.index(n)].IoConnectors[0].ConnectToIoSystem(ioSystem);



#
# # Compiling HW & SW
# 



# Defining method to recursively print error messages
# def print_comp(messages):
#     for msg in messages:
#         print(f'Path: {msg.Path}')
#         print(f'DateTime: {msg.DateTime}')
#         print(f'State: {msg.State}')
#         print(f'Description: {msg.Description}')
#         print(f'Warning Count: {msg.WarningCount}')
#         print(f'Error Count: {msg.ErrorCount}\n')
#         print_comp(msg.Messages)
    
# # Compiling all devices
# print('Compiling all devices')
# for device in myproject.Devices:
#     compile_service =  device.GetService[comp.ICompilable]()
#     result = compile_service.Compile()
                
#     #Printing results from compiler
#     print(f'State: {result.State}')
#     print(f'Warning Count: {result.WarningCount}')
#     print(f'Error Count: {result.ErrorCount}')
#     print_comp(result.Messages)   

        

#
# # Option to compile SW only
# 



# Defining method to recursively print error messages
# def print_comp(messages):
#     for msg in messages:
#         print(f'Path: {msg.Path}')
#         print(f'DateTime: {msg.DateTime}')
#         print(f'State: {msg.State}')
#         print(f'Description: {msg.Description}')
#         print(f'Warning Count: {msg.WarningCount}')
#         print(f'Error Count: {msg.ErrorCount}\n')
#         print_comp(msg.Messages)
    
#compiling all sw in all devices
# print('Importing XML file and compiling all SW in all devices')
# for device in myproject.Devices:
#     print(f'Processing device: {device.Name}')
    
#     # 检查设备类型是否为PLC
#     try:
#         # 获取设备的软件容器
#         plc_sw = None
#         for item in device.DeviceItems:
#             try:
#                 sw_container = tia.IEngineeringServiceProvider(item).GetService[hwf.SoftwareContainer]()
#                 if sw_container is not None:
#                     plc_sw = sw_container.Software
#                     break
#             except:
#                 continue
                
#         if plc_sw is None or device.Name == 'HM1': # and device.Name should not be HMI
#             print(f'Skipping device {device.Name}: No PLC software found')
#             continue
            
#         print(f'Found PLC software in device: {device.Name}')
        
#         # export existing scl as backup
#         # print('Exporting device existing function block into xml file...')
#         # plc_block = plc_sw.BlockGroup.Blocks.Find("BLOCK_1")
#         # if plc_block is not None:
#         #     plc_block.Export(FileInfo('E:\\pycharm-projects\\tia-openness\\exports\\BLOCK_1.xml'), tia.ExportOptions.WithDefaults)

#         # Import the XML file using absolute path
#         try:
#             print('Importing BLOCK_1.xml file...')
#             xml_path = os.path.abspath('exports\\BLOCK_1.xml')
#             print(f'Using absolute path: {xml_path}')
            
#             # 检查并删除已存在的FB
#             try:
#                 existing_block = plc_sw.BlockGroup.Blocks.Find("BLOCK_1")
#                 if existing_block is not None:
#                     print('Deleting existing BLOCK_1 block...')
#                     existing_block.Delete()
#             except Exception as e:
#                 print(f'Warning when checking existing block: {str(e)}')
            
#             # 导入新的FB

#             plc_sw.BlockGroup.Blocks.Import(FileInfo(xml_path), tia.ImportOptions.Override)
#             print('Successfully imported BLOCK_1.xml')
            
#             # 编译导入的块
#             print('Compiling imported block...')
#             compile_service = plc_sw.GetService[comp.ICompilable]()
#             result = compile_service.Compile()
            
#             # 打印编译结果
#             print(f'Compilation State: {result.State}')
#             print(f'Warning Count: {result.WarningCount}')
#             print(f'Error Count: {result.ErrorCount}')
#             if result.Messages is not None:
#                 print_comp(result.Messages)
                
#         except Exception as e:
#             print(f'Error during import/compile: {str(e)}')
#             continue
            
#     except Exception as e:
#         print(f'Error processing device {device.Name}: {str(e)}')
#         continue

# # Save the project after import and compilation
# print('Saving project...')
# myproject.Save()
# print('Project saved successfully')


# #
# # # Exporting 
# #     


# #Optional code to remove xml files that may allready exist on your computer
# try:
#     # E:\pycharm-projects\tia-openness
#     os.remove('E:\\pycharm-projects\\tia-openness\\exports\\dummy.xml')
# except OSError:
#     pass
# try:
#     os.remove('E:\\pycharm-projects\\tia-openness\\exports\\Main.xml')
# except OSError:
#     pass


# # exporting "main" from PLC1

# software_container = tia.IEngineeringServiceProvider(PLC1.DeviceItems[1]).GetService[hwf.SoftwareContainer]()
# software_base = software_container.Software

# # 检查是否存在Main程序块，如果存在则删除
# # try:
# #     existing_block = software_base.BlockGroup.Blocks.Find("Main")
# #     if existing_block is not None:
# #         existing_block.Delete()
# # except Exception as e:
# #     print(f"删除现有程序块时出错: {str(e)}")

# # 创建新的Main程序块（OB1）
# # try:
# #     plc_block = software_base.BlockGroup.Blocks.Create("Main", "OB", "SCL")
# #     print("成功创建Main程序块")
# # except Exception as e:
# #     print(f"创建程序块时出错: {str(e)}")
# #     plc_block = software_base.BlockGroup.Blocks.Find("Main")

# # 添加ST程序代码
# st_code = """
# VAR
#     // 全局变量
#     g_counter : INT := 0;    // 计数器
#     g_timer : TON;           // 定时器
#     g_pulse : BOOL;          // 脉冲信号
#     g_cycle_count : DINT;    // 周期计数
# END_VAR

# BEGIN
#     // 更新周期计数
#     g_cycle_count := g_cycle_count + 1;
    
#     // 使用定时器创建1秒的脉冲
#     g_timer(IN := NOT g_timer.Q,  // 当定时器完成时反转输入
#             PT := T#1S);          // 设置1秒的定时时间
    
#     // 当定时器完成时更新脉冲状态
#     IF g_timer.Q THEN
#         g_pulse := NOT g_pulse;   // 反转脉冲信号
        
#         // 在脉冲信号为TRUE时增加计数器
#         IF g_pulse THEN
#             g_counter := g_counter + 1;
#             // 计数器达到100时重置
#             IF g_counter >= 100 THEN
#                 g_counter := 0;
#             END_IF;
#         END_IF;
#     END_IF;
    
#     // 将值写入内存标记区，方便监控
#     "MW100" := g_counter;          // 计数器值 (INT)
#     "M102.0" := g_pulse;           // 脉冲状态 (BOOL)
#     "MD104" := g_cycle_count;      // 周期计数 (DINT)
# END_ORGANIZATION_BLOCK
# """

# # # 更新程序块的源代码
# # try:
# #     plc_block.UpdateSource(st_code)
# #     print("成功更新程序块源代码")
# # except Exception as e:
# #     print(f"更新源代码时出错: {str(e)}")

# # # 编译程序块
# # try:
# #     result = plc_block.Compile()
# #     if result.State == "Success":
# #         print("程序块编译成功")
# #         plc_block.Export(FileInfo('E:\\pycharm-projects\\tia-openness\\exports\\Main.xml'), tia.ExportOptions.WithDefaults)
# #     else:
# #         print(f"程序块编译警告/错误:")
# #         print_comp(result.Messages)
# # except Exception as e:
# #     print(f"编译程序块时出错: {str(e)}")



# # Exporting tagtable from PLC1
# tag_table_group = software_base.TagTableGroup
# # #creating a dummy table to export
# # tagtable = tag_table_group.TagTables.Create("dummy")
# tagtable = tag_table_group.TagTables.Find("dummy")
# # tagtable.Export(FileInfo('E:\\pycharm-projects\\tia-openness\\exports\\dummy.xml'), tia.ExportOptions.WithDefaults)


# #deleting block and tag table in project 
# # plc_block.Delete()
# # tagtable.Delete()


# #
# # # Importing
# # 



# # Importing the xml files back in to the project
# # tag_table_group.TagTables.Import(FileInfo('E:\\TIA_Projects\\test3\\exports\\dummy.xml'), tia.ImportOptions.Override)
# # software_base.BlockGroup.Blocks.Import(FileInfo('E:\\TIA_Projects\\test3\\exports\\Main.xml'), tia.ImportOptions.Override)




# myproject.Save()




# myproject.Close()




# mytia.Dispose()
