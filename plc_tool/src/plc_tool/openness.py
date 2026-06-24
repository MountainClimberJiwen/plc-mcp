import clr
import os
import time
import System
from System import IO

def check_dll_exists(dll_path):
    exists = os.path.exists(dll_path)
    if not exists:
        print(f"找不到DLL文件: {dll_path}")
    return exists

def init_env():
    """Initialize the TIA Portal and PLCSIM Advanced environment by loading required DLLs and checking paths."""
    # 添加 TIA Portal 和 PLCSIM Advanced 的所有必需 DLL 引用
    # 检查多个可能的安装路径
    possible_paths = [
        "E:\\Program Files\\Siemens\\Automation\\Portal V19\\Bin\\PublicAPI\\",
        "E:\\Program Files\\Siemens\\Automation\\Portal V19\\PublicAPI\\V19\\",
       # E:\Program Files\Siemens\Automation\PLCSIM_V19\resources\bin\wwwroot\assets\lib\runtime
    ]

    # 添加PLCSIM Advanced的路径
    plcsim_paths = [
        "E:\\Program Files\\Siemens\\Automation\\PLCSIM_V19\\bin\\",  # 主要的DLL路径
        "E:\\Program Files\\Siemens\\Automation\\PLCSIM_V19\\resources\\bin\\wwwroot\\assets\\lib\\runtime",  # 备用路径
        "C:\\Program Files\\Siemens\\Automation\\PLCSIM_V19\\bin\\",  # C盘路径
    ]

    tia_path = None
    plcsim_path = None

    # 检查TIA Portal路径
    for path in possible_paths:
        if os.path.exists(path):
            tia_path = path
            print(f"找到TIA Portal路径: {path}")
            break

    # 检查PLCSIM Advanced路径
    for path in plcsim_paths:
        if os.path.exists(path):
            plcsim_path = path
            print(f"找到PLCSIM Advanced路径: {path}")
            break

    if tia_path is None:
        raise Exception("未找到TIA Portal安装路径，请检查安装位置")

    if plcsim_path is None:
        print("警告: 未找到PLCSIM Advanced，请确保已安装PLCSIM Advanced")

    # 加载必需的DLL
    required_dlls = [
        'Siemens.Engineering.dll',
        'Siemens.Engineering.Contract.dll',
        # 'Siemens.Engineering.HW.dll',
        # 'Siemens.Engineering.HW.Contract.dll',
        # 'Siemens.Engineering.SW.dll',
        # 'Siemens.Engineering.SW.Contract.dll'
    ]

    # PLCSIM Advanced DLLs
    plcsim_dlls = [
        'Siemens.Simatic.Simulation.Runtime.Api.x64.dll'
    ]

    # 检查所有必需的DLL文件
    missing_dlls = []
    for dll in required_dlls:
        dll_path = os.path.join(tia_path, dll)
        print(f"正在检查DLL文件: {dll_path}")
        if not check_dll_exists(dll_path):
            missing_dlls.append(dll)
        else:
            print(f"成功找到并加载DLL: {dll}")
            clr.AddReference(dll_path)

    # 加载PLCSIM Advanced DLL
    if plcsim_path:
        # 尝试加载x86版本
        plcsim_dll_x86 = os.path.join(plcsim_path, 'Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
        
        if os.path.exists(plcsim_dll_x86):
            try:
                print(f"尝试加载x86 DLL: {plcsim_dll_x86}")
                clr.AddReference(plcsim_dll_x86)
                print("成功加载x86 DLL")
                
                # 在加载DLL后导入类
                from Siemens.Simatic.Simulation.Runtime import SimulationRuntimeManager
                from Siemens.Simatic.Simulation.Runtime import IInstance
                print("成功导入PLCSIM Advanced类")
                
            except Exception as dll_ex:
                print(f"加载PLCSIM Advanced DLL时出错: {str(dll_ex)}")
                print("详细错误信息:")
                import traceback
                print(traceback.format_exc())
        else:
            print(f"找不到PLCSIM Advanced DLL: {plcsim_dll_x86}")

    if missing_dlls:
        print("\n错误: 以下DLL文件缺失:")
        for dll in missing_dlls:
            print(f"  - {dll}")
        print("\n请检查:")
        print("1. TIA Portal V19是否正确安装")
        print("2. 是否安装了TIA Openness组件")
        print("3. 检查以下路径:")
        for path in possible_paths:
            print(f"   - {path}")
        raise Exception(f"缺少必需的DLL文件: {', '.join(missing_dlls)}")

    return tia_path, plcsim_path

# Initialize environment and get paths
TIA_PATH, PLCSIM_PATH = init_env()

from Siemens.Engineering import TiaPortal, TiaPortalMode, Project
from Siemens.Engineering.HW import Device, DeviceItem
from Siemens.Engineering.SW import PlcSoftware
from System import String, IO

def connect_to_plcsim_instance(project):
    """连接到已存在的PLCSIM实例"""
    try:
        # 获取PLCSIM管理器实例
        manager = SimulationRuntimeManager.CreateInstance()
        print("成功创建PLCSIM管理器实例")
        
        instance_name = "instance_1"  # 已创建的PLCSIM实例名称
        
        # 尝试查找现有实例
        instance = None
        try:
            instance = manager.RegisterInstance(instance_name)
            print(f"成功注册PLCSIM实例: {instance_name}")
        except:
            try:
                instance = manager.RegisteredInstanceInfo[0].Instance
                print(f"成功获取已存在的PLCSIM实例")
            except:
                print("无法注册或获取PLCSIM实例")
                return None
        
        if instance is None:
            print(f"找不到PLCSIM实例: {instance_name}")
            print("请确保PLCSIM Advanced已启动并创建了实例")
            return None
            
        # 确保实例处于正确的状态
        if instance.OperatingState != 1:  # 1 = OPERATING_STATE_RUN
            instance.PowerOn()  # 上电
            instance.Run()      # 运行
            print("PLCSIM实例已启动并运行")
            
        print(f"成功连接到PLCSIM实例: {instance_name}")
        return instance
        
    except Exception as e:
        print(f"连接PLCSIM实例时出错: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        print("\n请检查:")
        print("1. PLCSIM Advanced是否已启动")
        print("2. 是否已创建PLCSIM实例")
        return None
    finally:
        # 清理PLCSIM管理器实例
        try:
            if 'manager' in locals():
                manager.Dispose()
                print("已清理PLCSIM管理器实例")
        except Exception as e:
            print(f"清理PLCSIM管理器实例时出错: {str(e)}")

def create_new_project(tia_portal, project_path):
    """创建新的TIA Portal项目或加载现有项目"""
    try:
        project_dir = IO.Path.GetDirectoryName(project_path)
        project_name = IO.Path.GetFileNameWithoutExtension(project_path)
        
        # 检查目录是否存在且不为空
        if os.path.exists(project_dir) and os.listdir(project_dir):
            print(f"目录 {project_dir} 不为空，尝试加载现有项目...")
            # 查找目录中的 .ap19 文件
            for file in os.listdir(project_dir):
                if file.endswith(".ap19"):
                    existing_project_path = os.path.join(project_dir, file)
                    print(f"找到现有项目: {existing_project_path}")
                    try:
                        project = tia_portal.Projects.Open(IO.FileInfo(existing_project_path))
                        print(f"成功加载现有项目: {file}")
                        return project
                    except Exception as e:
                        print(f"加载项目 {file} 失败: {str(e)}")
                        continue
            
            print("目录中没有找到有效的TIA项目文件，将创建新项目")
            
        # 如果目录为空或没有找到有效项目，创建新项目
        print(f"在 {project_dir} 创建新项目: {project_name}")
        project = tia_portal.Projects.Create(IO.DirectoryInfo(project_dir), project_name)
        print(f"成功创建新项目: {project_name}")
        return project
        
    except Exception as e:
        print(f"创建/加载项目失败: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        return None

def add_plc_device(project, plcsim_instance=None):
    """添加PLC设备到项目"""
    try:
        device_name = "PLC_1"
        
        if plcsim_instance:
            # 从PLCSIM实例获取CPU类型
            cpu_type = plcsim_instance.CPUType
            print(f"PLCSIM CPU类型: {cpu_type}")
            
            # PLCSIM Advanced的CPU类型映射到TIA Portal型号
            cpu_type_mapping = {
                "CPU1500_Unspecified": "6ES7 511-1AK00-0AB0",  # CPU 1515-2 PN V2.9
                "CPU1511": "6ES7 511-1AK02-0AB0",              # CPU 1511-1 PN
                "CPU1511v2": "6ES7 511-1AK02-0AB0",           # CPU 1511-1 PN V2
                "CPU1513": "6ES7 513-1AL02-0AB0",              # CPU 1513-1 PN
                "CPU1515": "6ES7 515-2AH01-0AB0",              # CPU 1515-2 PN
                "CPU1516": "6ES7 516-3AN02-0AB0",              # CPU 1516-3 PN/DP
                "CPU1517": "6ES7 517-3AP00-0AB0",              # CPU 1517-3 PN/DP
            }
            
            # 获取对应的TIA Portal型号，如果找不到对应关系则使用默认的1515-2 PN
            type_name = cpu_type_mapping.get(str(cpu_type), "6ES7 511-1AK00-0AB0")
            print(f"选择的PLC型号: {type_name}")
        else:
            # 默认使用 CPU 1515-2 PN
            type_name = "6ES7 515-2AH01-0AB0"
            print("使用默认PLC型号: CPU 1515-2 PN")
       
        print("列出所有可用的设备类型:")
        if hasattr(project.Devices, 'Catalog'):
            print("列出所有可用的设备类型:")
            for device_type in project.Devices.Catalog.DeviceTypes:
                print(f"设备类型: {device_type.Name}, 订单号: {device_type.OrderNumber}")
        else:
            print("无法访问设备类型列表，请检查API文档以获取正确的方法")
        
        # 创建设备
        print(f"正在创建PLC设备，型号: {type_name}")
        device = project.Devices.CreateWithItem(type_name, device_name, device_name)
        print(f"成功添加PLC设备: {device_name}")
        
        # 获取PLC软件
        plc_software = None
        try:
            # 尝试获取设备项
            device_item = device.DeviceItems[0]
            print("成功获取设备项")
            
            # 尝试获取PLC软件
            plc_software = device_item.Software
            print("成功获取PLC软件")
            
            if plc_software is None:
                print("PLC软件为空，尝试其他方法...")
                try:
                    # 尝试通过GetService获取
                    plc_software = device.GetService(PlcSoftware)
                    print("通过GetService成功获取PLC软件")
                except Exception as e:
                    print(f"通过GetService获取PLC软件失败: {str(e)}")
                    try:
                        # 尝试直接访问Software属性
                        plc_software = device.Software
                        print("通过Software属性成功获取PLC软件")
                    except Exception as e:
                        print(f"直接访问Software属性失败: {str(e)}")
                        return None
        except Exception as e:
            print(f"获取PLC软件时出错: {str(e)}")
            print("详细错误信息:")
            import traceback
            print(traceback.format_exc())
            return None
        
        if plc_software is None:
            print("无法获取PLC软件")
            return None
            
        print("成功获取PLC软件")
        return device
        
    except Exception as e:
        print(f"添加PLC设备失败: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        return None


def create_st_program(plc_software):
    """创建ST程序"""
    try:
        # 创建新的程序块
        block_name = "Main"  # 使用Main作为主程序块
        
        # 检查是否已存在Main程序块
        existing_block = None
        for block in plc_software.BlockGroup.Blocks:
            if block.Name == block_name:
                existing_block = block
                break
        
        if existing_block is not None:
            program_block = existing_block
            print(f"使用现有程序块: {block_name}")
        else:
            program_block = plc_software.BlockGroup.Blocks.Create(block_name, "FB", "SCL")
            print(f"创建新程序块: {block_name}")
        
        # 设置程序块代码 - 一个简单的计数器程序
        st_code = """
FUNCTION_BLOCK "Main"
VAR
    counter : INT := 0;
    reset : BOOL;
END_VAR

BEGIN
    IF reset THEN
        counter := 0;
    ELSE
        counter := counter + 1;
        IF counter >= 100 THEN
            counter := 0;
        END_IF;
    END_IF;
END_FUNCTION_BLOCK
"""
        program_block.SetProgrammingLanguage("SCL")
        program_block.UpdateSource(st_code)
        
        # 编译程序块
        result = program_block.Compile()
        if result.Success:
            print("程序块编译成功")
        else:
            print("程序块编译失败:")
            for message in result.Messages:
                print(f"  - {message.Text}")
        
        return program_block
    except Exception as e:
        print(f"创建ST程序失败: {str(e)}")
        return None

# try:
#     # 创建TIA Portal实例
#     tia = TiaPortal(TiaPortalMode.WithoutUserInterface)
#     print("已启动TIA Portal")
    
#     # 设置项目路径
#     project_path = "E:\\TIA_Projects\\SimpleCounter\\SimpleCounter\\SimpleCounter.ap19"
    
#     # 创建新项目
#     project = create_new_project(tia, project_path)
#     if project:
#         # 添加PLC设备
#         device = add_plc_device(project)
#         if device:
#             # 获取PLC软件
#             plc_software = device.Software
            
#             if plc_software:
#                 # 创建ST程序
#                 program_block = create_st_program(plc_software)
                
#                 if program_block:
#                     # 保存项目
#                     project.Save()
#                     print("项目已保存")
                    
#                     # 尝试启动PLCSIM Advanced并下载程序
#                     plcsim_instance = connect_to_plcsim_instance(project)
#                     if plcsim_instance:
#                         print("准备下载程序到PLCSIM Advanced...")
#                         # TODO: 实现下载到PLCSIM Advanced的功能
#                     else:
#                         print("无法连接到PLCSIM Advanced，请确保它已正确启动")
#             else:
#                 print("无法获取PLC软件")
    
# except Exception as e:
#     print(f"操作失败: {str(e)}")
# finally:
#     # 关闭TIA Portal
#     if 'tia' in locals():
#         tia.Dispose()
#         print("已关闭TIA Portal")