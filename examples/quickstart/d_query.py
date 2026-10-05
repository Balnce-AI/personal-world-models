from common import PERSON, model
from pwm_hpl_ref.model_query import ModelQuery

with model() as pwm:
    print(pwm.query(ModelQuery((PERSON,))))
