import clr
from System.IO import DirectoryInfo, FileInfo

class Project:
    def __init__(self, project_path: str, project_name: str):
        """初始化Project类
        
        Args:
            project_path: TIA项目路径
            project_name: TIA项目名称
        """
        self.path_to_dll = 'E:\\Program Files\\Siemens\\Automation\\Portal V19\\Bin\\PublicAPI\\Siemens.Engineering.dll'
        self.project_path = project_path
        self.project_name = project_name
        clr.AddReference(self.path_to_dll)
        self.project = None

    def open_project(self):
        """打开TIA Portal项目
        
        Returns:
            成功打开项目返回True,否则返回False
        """
        print('Starting TIA with UI')
        import Siemens.Engineering as tia
        import Siemens.Engineering.HW.Features as hwf
        import Siemens.Engineering.Compiler as comp
        from System import IO

        # 获取所有运行的TIA Portal进程
        processes = tia.TiaPortal.GetProcesses()
        print(f'Found {len(processes)} TIA Portal processes')

        if len(processes) > 0:
            # 连接到第一个进程
            process = processes[0]
            mytia = process.Attach()
            
            # 检查是否有打开的项目
            if mytia is not None and mytia.Projects.Count > 0:
                myproject = mytia.Projects[0]
                print(f"Found open TIA project: {myproject.Name}")
                self.project = myproject
                return True
            else:
                print("No open TIA project found")
        else:
            print("No TIA Portal processes found")
            # 可以选择在这里启动新的TIA Portal实例
            # mytia = tia.TiaPortal(tia.TiaPortalMode.WithUserInterface)
            # project_path = self.project_path + '\\' + self.project_name + '\\' + self.project_name + '.ap19'
            # self.project = mytia.Projects.Open(IO.FileInfo(project_path))
        
        return False 