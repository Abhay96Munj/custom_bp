"""
User role group names — match the `name` field of auth.Group records.
These must stay in sync with the groups fixture (fixtures/roles.json).
"""

# Group name constants (formerly integer PKs)
ROLE_ADMIN       = 'Admin'
ROLE_USER        = 'User'         # default group for new signups
ROLE_SUPER_ADMIN = 'Super Admin'
ROLE_HR          = 'HR'
ROLE_MANAGER     = 'Manager'
ROLE_WORKER      = 'Worker'

# Permission codenames — follow 'resource_action' convention (underscores, no dots).
# These must match the codenames defined in User.Meta.permissions in models.py.
# Usage: user.has_perm('accounts.<codename>')
PERM_USER_VIEW    = 'user_view'
PERM_USER_CREATE  = 'user_create'
PERM_USER_EDIT    = 'user_edit'
PERM_USER_DELETE  = 'user_delete'
PERM_ROLE_MANAGE  = 'role_manage'
PERM_HR_VIEW      = 'hr_view'
PERM_REPORT_VIEW  = 'report_view'

"""
User Status
"""
USER_STATUS = (
    (1, "Active"),
    (2, "Inactive"),
    (3, "Deleted"),
    (4, "Suspended"),
    (5, "Terminated"),
)
ACTIVE     = 1
INACTIVE   = 2
DELETED    = 3
SUSPENDED  = 4
TERMINATED = 5

"""
GENDER
"""
GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]
MALE   = "M"
FEMALE = "F"
OTHER  = "O"

"""
Social Logins
"""
SOCIAL_TYPE = ((1, "Google"), (2, "Instagram"), (3, "Facebook"), (4, "Apple"))
GOOGLE    = 1
INSTAGRAM = 2
FACEBOOK  = 3
APPLE     = 4

NOTIFICATION_TYPES = (
    ("order",          "Order Update"),
    ("subscription",   "Subscription"),
    ("security",       "Security Alert"),
    ("system",         "System Message"),
    ("product_update", "Product Update"),
)