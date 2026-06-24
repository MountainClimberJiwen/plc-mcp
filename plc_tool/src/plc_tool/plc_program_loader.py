import os
import time
from sim_device import create_or_connect_instance
from openness import (
    TiaPortal,
    TiaPortalMode,
    create_new_project,
    add_plc_device,
    create_st_program
)
from System import IO, Type
from Siemens.Engineering.HW import Device, DeviceItem
from Siemens.Engineering.SW import PlcSoftware
from Siemens.Engineering.Compiler import ICompilable

def print_compilation_messages(messages, indent=0):
    """递归打印编译消息"""
    for msg in messages:
        prefix = "  " * indent
        print(f"{prefix}路径: {msg.Path}")
        print(f"{prefix}时间: {msg.DateTime}")
        print(f"{prefix}状态: {msg.State}")
        print(f"{prefix}描述: {msg.Description}")
        if msg.WarningCount > 0:
            print(f"{prefix}警告数: {msg.WarningCount}")
        if msg.ErrorCount > 0:
            print(f"{prefix}错误数: {msg.ErrorCount}")
        print()
        # 递归打印子消息
        if hasattr(msg, 'Messages'):
            print_compilation_messages(msg.Messages, indent + 1)

def compile_device(device):
    """编译设备并返回是否成功"""
    try:
        print(f"\n=== 编译设备: {device.Name} ===")
        # 获取编译服务
        compile_service = device.GetService[ICompilable]()
        if not compile_service:
            print("无法获取编译服务")
            return False
            
        # 执行编译
        result = compile_service.Compile()
        
        # 打印编译结果
        print(f"编译状态: {result.State}")
        if result.WarningCount > 0:
            print(f"警告数: {result.WarningCount}")
        if result.ErrorCount > 0:
            print(f"错误数: {result.ErrorCount}")
            
        # 打印详细消息
        if result.Messages and len(result.Messages) > 0:
            print("\n详细信息:")
            print_compilation_messages(result.Messages)
            
        # 根据编译结果返回
        return result.State == 'Success' and result.ErrorCount == 0
        
    except Exception as e:
        print(f"编译过程出错: {str(e)}")
        return False

def create_and_load_program():
    """创建或打开TIA项目并下载到PLCSIM实例"""
    tia = None
    instance = None
    manager = None
    
    try:
        # 1. 创建PLCSIM实例
        print("\n=== 创建PLCSIM实例 ===")
        instance, manager = create_or_connect_instance("PLCSIM_1")
        
        # 2. 创建或打开TIA Portal项目
        print("\n=== 初始化TIA Portal项目 ===")
        tia = TiaPortal(TiaPortalMode.WithUserInterface)
        print("已启动TIA Portal")
        
        # 设置项目路径
        project_path = "E:\\TIA_Projects\\SimpleCounter\\SimpleCounter\\SimpleCounter.ap19"
        print(f"项目路径: {project_path}")
        
        # 检查项目是否存在
        if os.path.exists(project_path):
            print("找到现有项目，正在打开...")
            project = tia.Projects.Open(IO.FileInfo(project_path))
            if not project:
                raise Exception("打开项目失败") 
            print("成功打开现有项目")
        else:
            print("项目不存在，创建新项目...")
            os.makedirs(os.path.dirname(project_path), exist_ok=True)
            project = create_new_project(tia, project_path)
            if not project:
                raise Exception("创建项目失败")
            print("成功创建新项目")
            
            # 只有新项目需要添加设备和创建程序
            print("\n=== 添加PLC设备 ===")
            device = add_plc_device(project, instance)
            if not device:
                raise Exception("添加PLC设备失败")
                
            print("\n=== 创建PLC程序 ===")
            # 获取PLC软件
            device_item = device.DeviceItems[0]
            plc_software = None
            try:
                plc_software = device_item.GetService("Software")
            except:
                try:
                    plc_software = device.GetService("Software")
                except:
                    pass
            
            if not plc_software:
                raise Exception("无法获取PLC软件")
                
            # 获取或创建Main OB
            main_ob = None
            for block in plc_software.BlockGroup.Blocks:
                if block.Name == "Main" and block.Type == "OB":
                    main_ob = block
                    print("找到现有Main OB")
                    break
            
            if main_ob is None:
                print("创建新的Main OB...")
                main_ob = plc_software.BlockGroup.Blocks.Create("Main", "OB", "SCL")
            
            # 设置一个简单的ST程序
            st_code = """
ORGANIZATION_BLOCK "Main"
VAR
    // 全局变量，可以在HMI或监控中查看
    g_counter : INT := 0;    // 计数器
    g_cycle_time : TIME;     // 周期时间
    g_cycle_count : DINT;    // 周期计数
END_VAR

VAR_TEMP
    temp_time : TIME;        // 临时时间变量
END_VAR

BEGIN
    // 更新周期计数
    g_cycle_count := g_cycle_count + 1;
    
    // 获取当前扫描周期时间
    temp_time := RUNTIME(#temp_time);
    g_cycle_time := temp_time;
    
    // 计数器逻辑
    g_counter := g_counter + 1;
    IF g_counter >= 100 THEN
        g_counter := 0;
    END_IF;
    
    // 将值写入内存标记区，方便监控
    "MW100" := g_counter;          // 计数器值 (INT)
    "MD104" := g_cycle_count;      // 周期计数 (DINT)
    "MD108" := DINT_TO_DWORD(TIME_TO_DINT(g_cycle_time));  // 周期时间 (TIME)
END_ORGANIZATION_BLOCK
"""
            # 设置编程语言并更新源代码
            main_ob.SetProgrammingLanguage("SCL")
            main_ob.UpdateSource(st_code)
            
            # 编译程序块和设备
            print("\n=== 编译程序 ===")
            # 首先编译程序块
            block_result = main_ob.Compile()
            if not block_result.Success:
                print("程序块编译失败:")
                print_compilation_messages(block_result.Messages)
                raise Exception("程序块编译失败")
            print("程序块编译成功")
            
            # 然后编译整个设备
            if not compile_device(device):
                raise Exception("设备编译失败")
            print("设备编译成功")
                
            # 保存新项目
            print("\n=== 保存项目 ===")
            project.Save()
            print("项目已保存")
        
        # 获取现有项目中的PLC设备
        if project.Devices.Count == 0:
            print("项目中没有找到PLC设备，添加新的PLC设备...")
            device = add_plc_device(project, instance)
            if not device:
                raise Exception("添加PLC设备失败")
            
            print("\n=== 创建PLC程序 ===")
            device_item = device.DeviceItems[0]
            plc_software = None
            try:
                plc_software = device_item.GetService("Software")
            except:
                try:
                    plc_software = device.GetService("Software")
                except:
                    pass
            
            if not plc_software:
                raise Exception("无法获取PLC软件")
                
            # 获取或创建Main OB
            main_ob = None
            for block in plc_software.BlockGroup.Blocks:
                if block.Name == "Main" and block.Type == "OB":
                    main_ob = block
                    print("找到现有Main OB")
                    break
            
            if main_ob is None:
                print("创建新的Main OB...")
                main_ob = plc_software.BlockGroup.Blocks.Create("Main", "OB", "SCL")
            
            # 设置一个简单的ST程序
            st_code = """
ORGANIZATION_BLOCK "Main"
VAR
    // 全局变量，可以在HMI或监控中查看
    g_counter : INT := 0;    // 计数器
    g_cycle_time : TIME;     // 周期时间
    g_cycle_count : DINT;    // 周期计数
END_VAR

VAR_TEMP
    temp_time : TIME;        // 临时时间变量
END_VAR

BEGIN
    // 更新周期计数
    g_cycle_count := g_cycle_count + 1;
    
    // 获取当前扫描周期时间
    temp_time := RUNTIME(#temp_time);
    g_cycle_time := temp_time;
    
    // 计数器逻辑
    g_counter := g_counter + 1;
    IF g_counter >= 100 THEN
        g_counter := 0;
    END_IF;
    
    // 将值写入内存标记区，方便监控
    "MW100" := g_counter;          // 计数器值 (INT)
    "MD104" := g_cycle_count;      // 周期计数 (DINT)
    "MD108" := DINT_TO_DWORD(TIME_TO_DINT(g_cycle_time));  // 周期时间 (TIME)
END_ORGANIZATION_BLOCK
"""
            # 设置编程语言并更新源代码
            main_ob.SetProgrammingLanguage("SCL")
            main_ob.UpdateSource(st_code)
            
            # 编译程序块和设备
            print("\n=== 编译程序 ===")
            # 首先编译程序块
            block_result = main_ob.Compile()
            if not block_result.Success:
                print("程序块编译失败:")
                print_compilation_messages(block_result.Messages)
                raise Exception("程序块编译失败")
            print("程序块编译成功")
            
            # 然后编译整个设备
            if not compile_device(device):
                raise Exception("设备编译失败")
            print("设备编译成功")
                
            # 保存项目更改
            print("\n=== 保存项目 ===")
            project.Save()
            print("项目已保存")
        else:
            device = project.Devices[0]
            print(f"找到PLC设备: {device.Name}")
            if not device:
                raise Exception("获取PLC设备失败")
            
            print("\n=== 获取PLC软件 ===")
            device_item = device.DeviceItems[0]
            plc_software = None
            try:
                plc_software = device_item.GetService("Software")
            except:
                try:
                    plc_software = device.GetService("Software")
                except:
                    pass
            
            if not plc_software:
                raise Exception("无法获取PLC软件")
       
        # 6. 下载到PLCSIM
        print("\n=== 下载到PLCSIM ===")
        # 获取PLC设备的下载提供程序
        download_provider = device.DeviceItems[0].GetService("DownloadProvider")
        if not download_provider:
            raise Exception("无法获取下载提供程序")
        
        # 配置下载设置
        download_provider.DownloadToDevice()
        print("程序已下载到PLCSIM实例")
        
        # 7. 等待下载完成
        time.sleep(5)
        
        # 8. 启动PLC
        print("\n=== 启动PLC ===")
        instance.PowerOn()
        time.sleep(2)
        instance.Run()
        
        # 9. 检查运行状态
        state = instance.OperatingState
        print(f"PLC运行状态: {state}")
        
        if state == 1:  # OPERATING_STATE_RUN
            print("PLC已成功启动并运行")
            return True
        else:
            print(f"PLC未能正确启动，当前状态: {state}")
            return False
            
    except Exception as e:
        print(f"操作失败: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        return False
        
    finally:
        # 清理资源
        if tia:
            tia.Dispose()
            print("已关闭TIA Portal")

if __name__ == "__main__":
    create_and_load_program() 