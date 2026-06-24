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

# PLCSIM Advanced的路径
plcsim_paths = [
   "E:\\Program Files\\Siemens\\Automation\\PLCSIM_V19\\resources\\bin\\wwwroot\\assets\\lib\\runtime",  # 备用路径
]

# 查找PLCSIM路径
PLCSIM_PATH = None
for path in plcsim_paths:
    if os.path.exists(path):
        PLCSIM_PATH = path
        print(f"找到PLCSIM Advanced路径: {path}")
        break

if PLCSIM_PATH is None:
    raise Exception("未找到PLCSIM Advanced，请确保已安装PLCSIM Advanced")

# 加载PLCSIM Advanced DLL
plcsim_dll_x64 = os.path.join(PLCSIM_PATH, 'Siemens.Simatic.Simulation.Runtime.Api.x64.dll')

if not os.path.exists(plcsim_dll_x64):
    raise Exception(f"找不到PLCSIM Advanced x64 DLL: {plcsim_dll_x64}")

try:
    print(f"尝试加载x64 DLL: {plcsim_dll_x64}")
    clr.AddReference(plcsim_dll_x64)
    print("成功加载x64 DLL")
    
    # 导入所需的类
    from Siemens.Simatic.Simulation.Runtime import SimulationRuntimeManager
    from Siemens.Simatic.Simulation.Runtime import IInstance
    from Siemens.Simatic.Simulation.Runtime import SDataValue
    print("成功导入PLCSIM Advanced类")

except Exception as e:
    print(f"加载PLCSIM Advanced DLL时出错: {str(e)}")
    print("详细错误信息:")
    import traceback
    print(traceback.format_exc())
    raise

def create_or_connect_instance(instance_name="PLCSIM_1"):
    """创建或连接到PLCSIM实例"""
    try:
        # 创建运行时管理器
        manager = SimulationRuntimeManager()
        print("成功创建PLCSIM管理器实例")
        
        # 检查现有实例
        registered_instances = manager.RegisteredInstanceInfo
        print(f"当前注册的实例数量: {len(registered_instances)}")
        
        instance = None
        
        # 首先尝试查找现有实例
        if len(registered_instances) > 0:
            for info in registered_instances:
                print(f"找到现有实例:")
                print(f"  名称: {info.Name}")
                print(f"  ID: {info.ID}")
                try:
                    # 尝试连接到现有实例
                    print(f"\n尝试连接到实例: {info.Name}")
                    # 使用RegisteredInstance而不是RegisterInstance
                    instance = manager.RegisteredInstance(info.Name)
                    if instance is not None:
                        print(f"成功连接到现有实例: {info.Name}")
                        return instance, manager
                except Exception as e:
                    print(f"连接到实例 {info.Name} 失败: {str(e)}")
                    continue
        
        # 如果没有找到可用的现有实例，尝试创建新实例
        if instance is None:
            try:
                # 在创建新实例前，先尝试清理所有实例
                try:
                    print("尝试清理所有现有实例...")
                    for info in registered_instances:
                        try:
                            print(f"正在注销实例: {info.Name}")
                            manager.UnregisterInstance(info.Name)
                            time.sleep(1)  # 等待实例注销完成
                        except:
                            print(f"注销实例 {info.Name} 失败，继续...")
                except:
                    print("清理实例过程中出错，继续...")
                
                print(f"\n尝试创建新实例: {instance_name}")
                instance = manager.RegisterInstance(instance_name)
                print(f"成功创建新的PLCSIM实例: {instance_name}")
            except Exception as e:
                print(f"创建新实例失败: {str(e)}")
                print("详细错误信息:")
                import traceback
                print(traceback.format_exc())
                raise
        
        if instance is None:
            raise Exception("无法创建或连接到PLCSIM实例")
            
        return instance, manager
        
    except Exception as e:
        print(f"创建/连接PLCSIM实例时出错: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        raise

def test_plc_operations(instance):
    """测试PLC基本操作"""
    try:
        # 等待实例完全初始化
        print("等待PLC实例初始化...")
        time.sleep(2)

        # 检查实例是否有效
        if instance is None:
            raise Exception("PLC实例无效")

        # 获取CPU类型
        cpu_type = instance.CPUType
        print(f"CPU类型: {cpu_type}")
        
        # 获取运行状态
        state = instance.OperatingState
        print(f"当前运行状态: {state}")
        
        # 检查是否已加载程序
        try:
            storage_state = instance.StorageState
            print(f"存储状态: {storage_state}")
            if storage_state == 0:  # StorageState.Empty
                print("警告: PLC中没有加载程序!")
                print("请先使用TIA Portal将程序下载到PLCSIM Advanced实例中")
                print("1. 在TIA Portal中打开您的项目")
                print("2. 在项目树中选择PLC")
                print("3. 右键点击PLC，选择'下载到设备'")
                print("4. 在'扩展下载到设备'对话框中：")
                print("   - 选择'PN/IE'作为类型")
                print("   - 选择正确的网卡")
                print("   - 选择PLCSIM实例（通常显示为'PLCSIM.XXX'）")
                print("5. 点击'加载'完成下载")
                return
        except Exception as e:
            print(f"检查存储状态时出错: {str(e)}")
            print("继续尝试启动流程...")
        
        # 正确的启动序列
        print("\n执行PLC启动序列:")
        
        try:
            # 直接尝试上电
            print("正在给PLC上电...")
            instance.PowerOn()
            time.sleep(2)  # 给予更多时间让PLC完成状态转换
            
            print("正在启动PLC...")
            try:
                instance.Run()
                time.sleep(2)  # 给予更多时间让PLC完成状态转换
            except Exception as e:
                if "IsEmpty" in str(e):
                    print("\n错误: PLC中没有加载程序，无法运行!")
                    print("请按照以下步骤操作：")
                    print("1. 确保已在TIA Portal中创建了项目")
                    print("2. 使用TIA Portal将程序下载到PLCSIM Advanced实例中")
                    print("3. 下载完成后再次尝试运行此程序")
                    return
                else:
                    raise
            
            # 检查最终状态
            final_state = instance.OperatingState
            print(f"PLC最终状态: {final_state}")
            
            if final_state == 1:  # OPERATING_STATE_RUN
                print("PLC已成功启动并运行")
                
                # 测试数据读写
                print("\n测试数据读写:")
                
                # 写入一个整数
                value = SDataValue()
                value.Int = 42
                instance.WriteBool("DB1.DBX0.0", True)  # 写入一个布尔值
                instance.WriteInt("DB1.DBW2", value.Int)  # 写入整数值
                print("已写入测试数据")
                
                # 读取数据
                bool_value = instance.ReadBool("DB1.DBX0.0")
                int_value = instance.ReadInt("DB1.DBW2")
                print(f"读取的布尔值: {bool_value}")
                print(f"读取的整数值: {int_value}")
            else:
                raise Exception(f"PLC未能达到运行状态，当前状态: {final_state}")
        except Exception as e:
            print(f"启动PLC时出错: {str(e)}")
            print("详细错误信息:")
            import traceback
            print(traceback.format_exc())
            raise
        
    except Exception as e:
        print(f"测试PLC操作时出错: {str(e)}")
        print("详细错误信息:")
        import traceback
        print(traceback.format_exc())
        raise

def main():
    try:
        print("Python版本和位数信息:")
        import platform
        print(f"Python 位数: {platform.architecture()[0]}")
        print(f"Python 版本: {platform.python_version()}")
        print()
        
        # 创建或连接到PLCSIM实例
        instance, manager = create_or_connect_instance()
        
        # 测试PLC操作
        test_plc_operations(instance)
        
        print("\n测试完成!")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
    finally:
        # 清理资源
        if 'manager' in locals():
            manager.Dispose()
            print("已释放PLCSIM管理器资源")

if __name__ == "__main__":
    main() 