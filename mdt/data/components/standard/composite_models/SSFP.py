from mdt.component_templates.composite_models import DMRICompositeModelTemplate


class SSFP_BallStick_r1_ExVivo(DMRICompositeModelTemplate):

    name = 'SSFP_BallStick_r1-ExVivo'
    description = 'The SSFP Ball & Stick model'
    model_expression = '''
        S0 * ( (Weight(w_ball) * SSFP_Ball) +
               (Weight(w_stick0) * SSFP_Stick(SSFP_Stick0)) )
    '''
    fixes = {'SSFP_Ball.d': 2.0e-9,
             'SSFP_Stick0.d': 0.6e-9,
             }
    post_optimization_modifiers = [('FS', lambda results: 1 - results['w_ball.w'])]


class SSFP_Tensor_ExVivo(DMRICompositeModelTemplate):

    name = 'SSFP_Tensor-ExVivo'
    description = 'The SSFP Tensor model with ex vivo defaults.'
    model_expression = '''
        S0 * SSFP_Tensor
    '''
    inits = {'SSFP_Tensor.d': 1e-9,
             'SSFP_Tensor.dperp0': 0.6e-10,
             'SSFP_Tensor.dperp1': 0.6e-10}
    volume_selection = None
