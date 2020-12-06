from athanor.utils.message import AdminMessage


class BBSMessage(AdminMessage):
    system_name = "CHANNEL"
    targets = ['enactor', 'target', 'user', 'admin']


class Create(BBSMessage):
    messages = {
        'enactor': "Successfully created {target_typename}: {target_fullname}",
        'target': "|w{enactor_name}|n created {target_typename}: {target_fullname}",
        'admin': "|w{enactor_name}|n created {target_typename}: {target_fullname}"
    }


class Rename(BBSMessage):
    messages = {
        'enactor': "Successfully renamed {target_typename}: {old_name} to {target_fullname}",
        'target': "|w{enactor_name}|n renamed {target_typename}: {old_name} to {target_fullname}",
        'admin': "|w{enactor_name}|n renamed {target_typename}: {old_name} to {target_fullname}"
    }


class Delete(BBSMessage):
    messages = {
        'enactor': "Successfully |rDELETED|n {target_typename}: {target_fullname}",
        'target': "|w{enactor_name}|n |rDELETED|n {target_typename}: {target_fullname}",
        'admin': "|w{enactor_name}|n |rDELETED|n {target_typename}: {target_fullname}"
    }


class Lock(BBSMessage):
    messages = {
        'enactor': "Successfully locked {target_typename}: {target_fullname} to: {lock_string}",
        'target': "|w{enactor_name}|n locked {target_typename}: {target_fullname} to: {lock_string}",
        'admin': "|w{enactor_name}|n locked {target_typename}: {target_fullname} to: {lock_string}"
    }


class Config(BBSMessage):
    messages = {
        'enactor': "Successfully re-configured {target_typename}: {target_fullname}. Set {config_op} to: {config_val}}",
        'target': "|w{enactor_name}|n re-configured {target_typename}: {target_fullname}. Set {config_op} to: {config_val}}",
        'admin': "|w{enactor_name}|n re-configured {target_typename}: {target_fullname}. Set {config_op} to: {config_val}}"
    }


class Grant(BBSMessage):
    pass


class Revoke(BBSMessage):
    pass


class Ban(BBSMessage):
    pass


class Unban(BBSMessage):
    pass
