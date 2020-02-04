from athanor.utils.message import AdminMessage


class ForumMessage(AdminMessage):
    system_name = "CHANNEL"
    targets = ['enactor', 'target', 'user', 'admin']


class Create(ForumMessage):
    messages = {
        'enactor': "Successfully created {target_typename}: {target_fullname}",
        'target': "|w{enactor_name}|n created {target_typename}: {target_fullname}",
        'admin': "|w{enactor_name}|n created {target_typename}: {target_fullname}"
    }


class Rename(ForumMessage):
    messages = {
        'enactor': "Successfully renamed {target_typename}: {old_name} to {target_fullname}",
        'target': "|w{enactor_name}|n renamed {target_typename}: {old_name} to {target_fullname}",
        'admin': "|w{enactor_name}|n renamed {target_typename}: {old_name} to {target_fullname}"
    }


class Delete(ForumMessage):
    messages = {
        'enactor': "Successfully |rDELETED|n {target_typename}: {target_fullname}",
        'target': "|w{enactor_name}|n |rDELETED|n {target_typename}: {target_fullname}",
        'admin': "|w{enactor_name}|n |rDELETED|n {target_typename}: {target_fullname}"
    }


class Lock(ForumMessage):
    messages = {
        'enactor': "Successfully locked {target_typename}: {target_fullname} to: {lock_string}",
        'target': "|w{enactor_name}|n locked {target_typename}: {target_fullname} to: {lock_string}",
        'admin': "|w{enactor_name}|n locked {target_typename}: {target_fullname} to: {lock_string}"
    }


class Config(ForumMessage):
    messages = {
        'enactor': "Successfully re-configured {target_typename}: {target_fullname}. Set {config_op} to: {config_val}}",
        'target': "|w{enactor_name}|n re-configured {target_typename}: {target_fullname}. Set {config_op} to: {config_val}}",
        'admin': "|w{enactor_name}|n re-configured {target_typename}: {target_fullname}. Set {config_op} to: {config_val}}"
    }


class Grant(ForumMessage):
    pass


class Revoke(ForumMessage):
    pass


class Ban(ForumMessage):
    pass


class Unban(ForumMessage):
    pass
