# Example 1 — Bad style: naming violations, spacing issues, long lines
import os,sys
import json

class user_account:  # N801: should be UserAccount
    def __init__(self,name,email,age):
        self.name=name
        self.email=email
        self.age=age

    def GetFullInfo(self):  # N802: should be get_full_info
        return f"User: {self.name}, Email: {self.email}, Age: {self.age}, System: {os.name}, Python: {sys.version}"

    def ValidateEmail(self):  # N802: should be validate_email
        if "@" in self.email and "." in self.email:
            return True
        return False

    def UpdateProfile(self,new_name,new_email):  # N802, E231 (missing spaces after commas)
        self.name=new_name
        self.email=new_email


class adminUser(user_account):  # N801: should be AdminUser
    def __init__(self,name,email,age,admin_level):
        super().__init__(name,email,age)
        self.admin_level=admin_level

    def GetPermissions(self):  # N802: should be get_permissions
        perms=[]
        if self.admin_level==1:
            perms=["read"]
        elif self.admin_level==2:
            perms=["read","write"]
        elif self.admin_level==3:
            perms=["read","write","delete","admin","superuser","root"]
        return perms


def ProcessUsers(users):  # N802
    results=[]
    for u in users:
        if u.ValidateEmail():
            results.append(u.GetFullInfo())
    return results


def loadConfig(filepath):  # N802
    with open(filepath) as f:
        data=json.load(f)
    return data
