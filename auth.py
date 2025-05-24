from models import Salesperson

class AuthManager:
    @staticmethod
    def login(salesperson_id, password):
        """
        简化版登录验证
        参数:
            salesperson_id: 销售人员ID
            password: 明文密码
        返回:
            验证成功返回Salesperson对象，失败返回None
        """
        salesperson_data = Salesperson.find_one({"salesperson_id": salesperson_id})
        
        if not salesperson_data:
            print("销售人员ID不存在")
            return None
            
        # 简化验证：直接比较明文密码
        if password == salesperson_data['password_hash']:
            print(f"登录成功: {salesperson_data['salesperson_name']} ({salesperson_data['role']})")
            return Salesperson(**salesperson_data)
        else:
            print("密码错误")
            return None

    @staticmethod
    def register_salesperson(salesperson_id, name, contact, email, password, role='Salesperson'):
        """
        简化版注册功能
        参数:
            salesperson_id: 销售人员ID
            name: 姓名
            contact: 联系方式
            email: 电子邮箱
            password: 明文密码
            role: 角色(默认'Salesperson')
        返回:
            注册成功返回Salesperson对象，失败返回None
        """
        if Salesperson.find_one({"salesperson_id": salesperson_id}):
            print(f"销售人员ID '{salesperson_id}' 已存在")
            return None
            
        new_salesperson = Salesperson(
            salesperson_id=salesperson_id,
            salesperson_name=name,
            contact_number=contact,
            email=email,
            password_hash=password,  # 直接存储明文密码
            role=role
        )
        
        if new_salesperson.save():
            print(f"销售人员 '{name}' 注册成功")
            return new_salesperson
        else:
            print("注册失败")
            return None