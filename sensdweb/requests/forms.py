#forms.py ___ this forms are for the request form that saves data to files 


from django import forms
from .models import Request, AllNodes, InitialNodes, FinishedGoods, Arc , PathogenTestingMethod, PathogenTestingMethodFNodes, DynamicParameters


class AllNodeForm(forms.ModelForm):
    class Meta:
        model = AllNodes
        fields = ['node_id','node_name', 'probability', 'cumulative_cost', 'demand_rate']
        widgets = {
            'node_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'node_name': forms.TextInput(attrs={'class': 'form-control'}),
            'probability': forms.NumberInput(attrs={'class': 'form-control'}),
            'cumulative_cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'demand_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'node_id': 'Node ID',
            'node_name': 'Node Name',
            'probability': 'Probability',
            'cumulative_cost': 'Cumulative Cost',
            'demand_rate': 'Demand Rate',
        }

class InitialNodeForm(forms.ModelForm):
    class Meta:
        model = InitialNodes
        fields = ['node_id', 'node_name']
        widgets = {
            'node_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'node_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'node_id': 'Node ID',
            'node_name': 'Node Name',
        }

class FinishedGoodsForm(forms.ModelForm):
    class Meta:
        model = FinishedGoods
        fields = ['node_id', 'node_name', 'demand_rate']
        widgets = {
            'node_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'node_name': forms.TextInput(attrs={'class': 'form-control'}),
            'demand_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'node_id': 'Node ID',
            'node_name': 'Node Name',
            'demand_rate': 'Demand Rate',
        }

class ArcForm(forms.ModelForm):
    class Meta:
        model = Arc
        fields = ['Arc_id','from_node_id','from_node_name', 'to_node_id','to_node_name', 'multiplier']
        widgets = {
            'Arc_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'from_node_name' : forms.TextInput(attrs={'class': 'form-control'}),
            'from_node_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'to_node_name' : forms.TextInput(attrs={'class': 'form-control'}),
            'to_node_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'multiplier': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'Arc_id': 'ID',
            'from_node_name': 'From Node Name',
            'from_node_id': 'From Node ID',
            'to_node_name': 'To Node Name',
            'to_node_id': 'To Node ID',
            'multiplier': 'Mutliplier',
        }

class PathogenTestingMethodForm(forms.ModelForm):
    class Meta:
        model = PathogenTestingMethod
        fields = [ 'ptm_id','pathogen_testing_method']
        widgets = {
            'ptm_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'pathogen_testing_method': forms.TextInput(attrs={'class': 'form-control'}),           
        }
        labels = {
            'ptm_id': 'ID',
            'pathogen_testing_method': 'Pathogen Testing Method',
        }

class PathogenTestingMethodFNodesForm(forms.ModelForm):
    class Meta:
        model = PathogenTestingMethodFNodes
        fields = ['node_id','pathogen_testing_method_id', 'sensitivity', 'direct_cost', 'lead_time']
        widgets = {
            'node_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'pathogen_testing_method_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'sensitivity': forms.NumberInput(attrs={'class': 'form-control'}),
            'direct_cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'lead_time': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'node_id': 'ID',
            'pathogen_testing_method_id': 'Pathogen Testing Method ID',
            'sensitivity': 'Sensitivity',
            'direct_cost': 'Direct Cost',
            'lead_time': 'Lead time',
        }

class DynamicParametersForm(forms.ModelForm):
    class Meta:
        model = DynamicParameters
        fields = ['dynamic_parameter_id', 'maxsteps_k', 'maxpercentage_alpha', 'maxbudget_B']       
        # Optional: You can also customize the form fields by using widgets or setting labels.
        widgets = {
            'dynamic_parameter_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'maxsteps_k': forms.NumberInput(attrs={'class': 'form-control'}),
            'maxpercentage_alpha': forms.NumberInput(attrs={'class': 'form-control'}),
            'maxbudget_B': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'dynamic_parameter_id': 'Dynamic Parameter ID',
            'maxsteps_k': 'Max Steps (k)',
            'maxpercentage_alpha': 'Max Percentage (Alpha)',
            'maxbudget_B': 'Max Budget (B)',
        }