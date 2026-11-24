from domain.jigs_api import router as jigs
from domain.coupons_api import router as coupons
from domain.profiles_api import router as profiles
from domain.work_orders_api import router as work_orders

routers = (jigs, coupons, profiles, work_orders,)
