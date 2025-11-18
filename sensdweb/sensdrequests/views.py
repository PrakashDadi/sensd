import pandas as pd
import os

from django.shortcuts import render , redirect , get_object_or_404
from django.utils.encoding import force_bytes , DjangoUnicodeDecodeError , force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.urls import reverse
from django.contrib import messages
from django.core.mail import EmailMessage

from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from django.forms import formset_factory
from django.utils import timezone

from django.http import HttpResponse , JsonResponse

from .models import Request as RequestModel, AllNodes, InitialNodes, FinishedGoods, Arc, PathogenTestingMethod , PathogenTestingMethodFNodes, DynamicParameters, ResultModel , NodeResult, VariableResult
from .forms import AllNodeForm, InitialNodeForm, FinishedGoodsForm, ArcForm, PathogenTestingMethodForm , PathogenTestingMethodFNodesForm, DynamicParametersForm

from django.core.files.storage import FileSystemStorage

from django.conf import settings

from datetime import datetime


import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from collections import defaultdict, deque #Used to create dictionaries with default values and double-ended queues

from django.forms import formset_factory
from .forms import DynamicParametersForm

from io import BytesIO
import re
# Create your views here.

import matplotlib.pyplot as plt
import base64

import json

from authentication.models import UserKey
from authentication.utils import encrypt_data, decrypt_data

from django.contrib.auth import get_user_model
User = get_user_model()

import json

def newRequest(request):
    uservalues =  request.session.get('uservalues', None)
    user_key = UserKey.objects.get(user=uservalues['pk'])
    public_key = user_key.public_key

    if uservalues is None:
        messages.error(request,'Something went wrong, Cant Raise a request')
        return redirect('sensd')
    
    email = uservalues['email']
    # username = urlsafe_base64_encode(force_bytes(uservalues['username']))
    requested_date = uservalues.get('requested_date', datetime.now().strftime('%Y%m%d'))

    print("requested date", requested_date)
    new_request = RequestModel(
        user_request_id = f"Request{requested_date}",  # Generate or assign a unique value
        created_by=email,  # Assuming user is authenticated
        updated_by=email,
        created_on=timezone.now(),
        updated_on=timezone.now(),
        is_deleted=False
    )
    print("Before saving new request", new_request.is_deleted)
    new_request.save()


    
    new_request.user_request_id = f"Request{requested_date}{new_request.request_id}"
    new_request.save()

    messages.success(request, 'New Request Initiated')
    return redirect(reverse('AllNodes', kwargs={'requestid': new_request.user_request_id}))
    
    
    
def allNodes(request, requestid):
    uservalues =  request.session.get('uservalues', None)
    user_key = UserKey.objects.get(user=uservalues['pk'])
    public_key = user_key.public_key
    private_key = user_key.private_key
   # Initialize an empty form
    all_node_form = AllNodeForm()

    if request.method == 'POST':
        # Bind form with POST data
        all_node_form = AllNodeForm(request.POST)
        if all_node_form.is_valid():
            # Save the form data to the database
            new_node = all_node_form.save(commit=False)
            new_node.user_request_id = requestid
            new_node.created_by = request.user.email
            new_node.updated_by = request.user.email
            new_node.save()
            
            # Redirect to the same page to display the new data
            return redirect('AllNodes', requestid=requestid)
        
    # Retrieve all nodes associated with the request ID
    nodes = AllNodes.objects.filter(user_request_id=requestid)
    
    return render(request, 'userrequests/all_nodes.html', {
        'requestid': requestid,
        'form': all_node_form,
        'nodes': nodes,
    })



def edit_allnode(request, pk, requestid):


    node = get_object_or_404(AllNodes, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = AllNodeForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('AllNodes', requestid=requestid)
    else:
        form = AllNodeForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = AllNodes.objects.filter(user_request_id=requestid, is_deleted=False)
    
    return render(request, 'userrequests/all_nodes.html', {
        'requestid': requestid,
        'form': form,
        'nodes': nodes,
    })




def initialNodes(request, requestid):
    InitialNodeFormSet = formset_factory(InitialNodeForm, extra=1)
    
    print("request Id at initailnodes", requestid)

    if request.method == 'POST':
        # Bind form with POST data
        initial_node_form = InitialNodeFormSet(request.POST)
        if initial_node_form.is_valid():
            for form in initial_node_form:
            # Save the form data to the database
                new_node = form.save(commit=False)
                new_node.user_request_id = requestid
                new_node.created_by = request.user.email
                new_node.updated_by = request.user.email
                new_node.save()
                
                # Redirect to the same page to display the new data
            return redirect('InitialNodes', requestid=requestid)
    else:
        # Initialize an empty formset
        initial_node_form = InitialNodeFormSet()

    initialnodes = InitialNodes.objects.filter(user_request_id=requestid)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/initial_nodes.html', {'uservalues': uservalues, 'formset': initial_node_form, 'initial_nodes': initialnodes, 'requestid': requestid})

def edit_initialNodes(request, pk, requestid):

    node = get_object_or_404(InitialNodes, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = InitialNodeForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('InitialNodes', requestid=requestid)
    else:
        form = InitialNodeForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = InitialNodes.objects.filter(user_request_id=requestid, is_deleted=False)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/initial_nodes.html', {
        'uservalues': uservalues,
        'requestid': requestid,
        'formset': form,
        'initial_nodes': nodes,
    })



def dynamicparametersform(request, requestid):
    # Use formset_factory with your form
    DynamicParametersFormSet = formset_factory(DynamicParametersForm, extra=1)

    if request.method == 'POST':
        # Bind the formset with POST data
        formset = DynamicParametersFormSet(request.POST)
        
        if formset.is_valid():
            # Save the form data to the database
            for form in formset:
                new_node = form.save(commit=False)  # Don't save immediately
                new_node.user_request_id = requestid
                new_node.created_by = request.user.email
                new_node.updated_by = request.user.email
                new_node.save()  # Now save the instance to the database

            # Redirect to the same page to display the new data
            return redirect('DynamicParameterForm', requestid=requestid)
        else:
            print("Formset errors:", formset.errors)  # This will print formset errors for debugging
    
    else:
        # Empty formset on GET request
        formset = DynamicParametersFormSet()

    # Retrieve all nodes associated with the request ID
    dynamicparameter = DynamicParameters.objects.filter(user_request_id=requestid)

    return render(request, 'userrequests/dynamic_parameters.html', {
        'requestid': requestid,
        'formset': formset,
        'nodes': dynamicparameter,
    })



def finishedGoods(request, requestid):
    FinishedGoodsFormSet = formset_factory(FinishedGoodsForm, extra=1)

    print("request Id at finshednodes", requestid)

    if request.method == 'POST':
        # Bind form with POST data
        finished_goods_formset = FinishedGoodsFormSet(request.POST)
        if finished_goods_formset.is_valid():
            for form in finished_goods_formset:
            # Save the form data to the database
                new_node = form.save(commit=False)
                new_node.user_request_id = requestid
                new_node.created_by = request.user.email
                new_node.updated_by = request.user.email
                new_node.save()
                
                # Redirect to the same page to display the new data
            return redirect('FinishedGoods', requestid=requestid)
    else:
        # Initialize an empty formset
        finished_goods_formset = FinishedGoodsFormSet()

    finished_goods = FinishedGoods.objects.filter(user_request_id=requestid)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/finishedgoods.html', {'uservalues': uservalues, 'formset': finished_goods_formset, 'finished_goods': finished_goods, 'requestid': requestid})

def edit_finishedGoods(request, pk, requestid):

    node = get_object_or_404(FinishedGoods, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = FinishedGoodsForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('FinishedGoods', requestid=requestid)
    else:
        form = FinishedGoodsForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = FinishedGoods.objects.filter(user_request_id=requestid, is_deleted=False)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/finishedgoods.html', {
        'uservalues': uservalues,
        'requestid': requestid,
        'formset': form,
        'finished_goods': nodes,
    })

def arcform(request, requestid):

    arc_form_set = formset_factory(ArcForm,extra=1)
    
    print("request Id at arcform", requestid)

    if request.method == 'POST':
        # Bind form with POST data
        arc_formset = arc_form_set(request.POST)
        if arc_formset.is_valid():
            for form in arc_formset:
            # Save the form data to the database
                new_node = form.save(commit=False)
                new_node.user_request_id = requestid
                new_node.created_by = request.user.email
                new_node.updated_by = request.user.email
                new_node.save()
                
                # Redirect to the same page to display the new data
            return redirect('ARCForm', requestid=requestid)
    else:
        # Initialize an empty formset
        arc_formset = arc_form_set()

    arcs = Arc.objects.filter(user_request_id=requestid)   
    return render(request, 'userrequests/arcs.html', {'formset': arc_formset, 'arcs': arcs , 'requestid': requestid })

def edit_arcform(request, pk, requestid):

    node = get_object_or_404(Arc, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = ArcForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('ARCForm', requestid=requestid)
    else:
        form = ArcForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = Arc.objects.filter(user_request_id=requestid, is_deleted=False)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/arcs.html', {
        'uservalues': uservalues,
        'requestid': requestid,
        'formset': form,
        'arcs': nodes,
    })

def pathtestmethodform(request, requestid):

    ptm_form_set = formset_factory(PathogenTestingMethodForm, extra=1)

    print("request Id at arcform", requestid)

    if request.method == 'POST':
        # Bind form with POST data
        ptm_formset = ptm_form_set(request.POST)
        if ptm_formset.is_valid():
            for form in ptm_formset:
            # Save the form data to the database
                new_node = form.save(commit=False)
                new_node.user_request_id = requestid
                new_node.created_by = request.user.email
                new_node.updated_by = request.user.email
                new_node.save()
                
                # Redirect to the same page to display the new data
            return redirect('PTMForm', requestid=requestid)
    else:
        # Initialize an empty formset
        ptm_formset = ptm_form_set()

    ptmNodeFormValues = PathogenTestingMethod.objects.filter(user_request_id=requestid)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/pathogen_testing_methods.html', {'uservalues': uservalues, 'formset': ptm_formset, 'pathogen_testing_methods': ptmNodeFormValues,  'requestid': requestid })

def edit_pathtestmethodform(request, pk, requestid):

    node = get_object_or_404(PathogenTestingMethod, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = PathogenTestingMethodForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('PTMForm', requestid=requestid)
    else:
        form = PathogenTestingMethodForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = PathogenTestingMethod.objects.filter(user_request_id=requestid, is_deleted=False)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/pathogen_testing_methods.html', {
        'uservalues': uservalues,
        'requestid': requestid,
        'formset': form,
        'pathogen_testing_methods': nodes,
    })


def pathtestmethodFnodesform(request , requestid):

    ptm_fnode_formset = formset_factory(PathogenTestingMethodFNodesForm, extra=1)

    if request.method == 'POST':
        # Bind form with POST data
        ptm_fnode_form_set = ptm_fnode_formset(request.POST)
        if ptm_fnode_form_set.is_valid():
            for form in ptm_fnode_form_set:
            # Save the form data to the database
                new_node = form.save(commit=False)
                new_node.user_request_id = requestid
                new_node.created_by = request.user.email
                new_node.updated_by = request.user.email
                new_node.save()
                
                # Redirect to the same page to display the new data
            return redirect('PTMFNodesForm', requestid=requestid)
    else:
        # Initialize an empty formset
        ptm_fnode_form_set = ptm_fnode_formset()

    ptmFNodeValues = PathogenTestingMethodFNodes.objects.filter(user_request_id=requestid)

    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/pathogen_testing_method_fnodes.html', {
        'uservalues': uservalues, 
        'formset': ptm_fnode_form_set, 
        'pathogen_testing_method_fnodes': ptmFNodeValues, 
        'requestid': requestid 
        })

def edit_pathtestmethodFnodesform(request, pk, requestid):

    node = get_object_or_404(PathogenTestingMethodFNodes, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = PathogenTestingMethodFNodesForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('PTMFNodesForm', requestid=requestid)
    else:
        form = PathogenTestingMethodFNodesForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = PathogenTestingMethodFNodes.objects.filter(user_request_id=requestid, is_deleted=False)
    uservalues =  request.session.get('uservalues', None)
    
    return render(request, 'userrequests/pathogen_testing_method_fnodes.html', {
        'uservalues': uservalues,
        'requestid': requestid,
        'formset': form,
        'pathogen_testing_method_fnodes': nodes,
    })

def generate_excel(request, requestid):
    user_request_id = requestid
    
    # Get the corresponding request object
    request_obj = get_object_or_404(RequestModel, user_request_id=user_request_id)
    
    # Specify the fields to include and their corresponding column names in the Excel
    all_nodes_fields = {
        'node_id': 'ID', 
        'node_name': 'Node Name', 
        'probability': 'Probability',
        'cumulative_cost': 'Cumulative Cost',
        'demand_rate': 'Demand Rate'
    }
    initial_nodes_fields = {
        'node_id': 'Node ID', 
        'node_name': 'Node Name'
    }
    finished_goods_fields = {
        'node_id': 'Node ID', 
        'node_name': 'Node Name', 
        'demand_rate': 'Demand Rate'
    }
    arcs_fields = {
        'Arc_id': 'ID', 
        'from_node_id': 'From Node ID',
        'from_node_name': 'From Node Name', 
        'to_node_id': 'To Node ID',
        'to_node_name': 'To Node Name',
        'multiplier': 'Multiplier'
    }
    ptm_fields = {
        'ptm_id': 'ID', 
        'pathogen_testing_method': 'Pathogen Testing Methods'
    }
    ptm_f_nodes_fields = {
        'node_id': 'Node ID', 
        'pathogen_testing_method_id': 'Pathogen Testing Method ID', 
        'sensitivity': 'Sensitivity',
        'direct_cost':'Direct Cost',
        'lead_time': 'Lead Time'
    }
    dynamic_parameters_feilds = {
        'dynamic_parameter_id' : 'ID',
        'maxsteps_k' : 'Max Steps (K)',
        'maxpercentage_alpha' : 'Max Percentage (Alpha)',
        'maxbudget_B' : 'Max Budget (B)',
    }
    
    # Collect data from each model and rename columns
    all_nodes = AllNodes.objects.filter(user_request_id=user_request_id).values(*all_nodes_fields.keys())
    initial_nodes = InitialNodes.objects.filter(user_request_id=user_request_id).values(*initial_nodes_fields.keys())
    finished_goods = FinishedGoods.objects.filter(user_request_id=user_request_id).values(*finished_goods_fields.keys())
    arcs = Arc.objects.filter(user_request_id=user_request_id).values(*arcs_fields.keys())
    pathogen_testing_methods = PathogenTestingMethod.objects.filter(user_request_id=user_request_id).values(*ptm_fields.keys())
    pathogen_testing_method_f_nodes = PathogenTestingMethodFNodes.objects.filter(user_request_id=user_request_id).values(*ptm_f_nodes_fields.keys())
    dynamic_parameters = DynamicParameters.objects.filter(user_request_id=user_request_id).values(*dynamic_parameters_feilds.keys())
    
    # Create a Pandas Excel writer using Openpyxl
    output_file_path = f"media/excels/{user_request_id}_data.xlsx"
    writer = pd.ExcelWriter(output_file_path, engine='openpyxl')

    sheet_written = False
    
    # Convert QuerySets to DataFrames and rename columns
    if all_nodes:
        all_nodes_df = pd.DataFrame(list(all_nodes))
        all_nodes_df.rename(columns=all_nodes_fields, inplace=True)
        all_nodes_df.to_excel(writer, sheet_name='All Nodes', index=False)
        sheet_written = True
    
    if initial_nodes:
        initial_nodes_df = pd.DataFrame(list(initial_nodes))
        initial_nodes_df.rename(columns=initial_nodes_fields, inplace=True)
        initial_nodes_df.to_excel(writer, sheet_name='Initial Nodes', index=False)
        sheet_written = True
    
    if finished_goods:
        finished_goods_df = pd.DataFrame(list(finished_goods))
        finished_goods_df.rename(columns=finished_goods_fields, inplace=True)
        finished_goods_df.to_excel(writer, sheet_name='Finished Products', index=False)
        sheet_written = True
    
    if arcs:
        arcs_df = pd.DataFrame(list(arcs))
        arcs_df.rename(columns=arcs_fields, inplace=True)
        arcs_df.to_excel(writer, sheet_name='Arcs', index=False)
        sheet_written = True
    
    if pathogen_testing_methods:
        ptm_df = pd.DataFrame(list(pathogen_testing_methods))
        ptm_df.rename(columns=ptm_fields, inplace=True)
        ptm_df.to_excel(writer, sheet_name='Pathogen Testing Methods', index=False)
        sheet_written = True
    
    if pathogen_testing_method_f_nodes:
        ptm_f_nodes_df = pd.DataFrame(list(pathogen_testing_method_f_nodes))
        ptm_f_nodes_df.rename(columns=ptm_f_nodes_fields, inplace=True)
        ptm_f_nodes_df.to_excel(writer, sheet_name='Pathogen Testing Methods F Node', index=False)
        sheet_written = True

    if dynamic_parameters:
        dynamic_parameters_df = pd.DataFrame(list(dynamic_parameters))
        dynamic_parameters_df.rename(columns=dynamic_parameters_feilds, inplace=True)
        dynamic_parameters_df.to_excel(writer, sheet_name='Dynamic Parameters', index=False)
        sheet_written = True
    
    if not sheet_written:
        pd.DataFrame([["No data available for this request."]]).to_excel(writer, sheet_name="No Data", index=False)
    # Save the Excel file
    writer.close()
    
    # Save the path to the Request model
    request_obj.final_excel = output_file_path
    request_obj.save()
    
    # Optionally, return the file as a response
    with open(output_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={user_request_id}_data.xlsx'
        return response

    
def user_requests(request):
    uservalues =  request.session.get('uservalues', None)
    if uservalues is None:
        messages.error(request, 'Session expired or invalid.')
        return redirect('login')
    
    user_key = UserKey.objects.get(user=uservalues['pk'])
    private_key = user_key.private_key

    print("Session uservalues retrieved:", uservalues)
    print("Session uservalues retrieved:", uservalues['email'])

    all_requests = RequestModel.objects.all()
    user_requests = []

    for req in all_requests:
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(req.created_by))
            if decrypted_created_by == uservalues['email']:
                req.created_by = decrypted_created_by  # Optional: for display
                user_requests.append(req)
        except Exception as e:
            print("Decryption failed for a request:", e)

    all_results = ResultModel.objects.all()
    user_results = []

    for req in all_results:
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(req.created_by))
            if decrypted_created_by == uservalues['email']:
                req.created_by = decrypted_created_by  # Optional: for display
                user_results.append(req)
        except Exception as e:
            print("Decryption failed for a result:", e)

    return render(request, 'userrequests/requests_list_history.html', {
        'uservalues': uservalues,
        'requests': user_requests,
        'results': user_results
    })

def uploadexcel(request):
    uservalues =  request.session.get('uservalues', None)

    return render(request, 'userrequests/uploadexcel.html', {'uservalues': uservalues })

def viewexceldata(request):
    
    uservalues =  request.session.get('uservalues', None)

    if request.method == 'POST':
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            file_url = fs.url(filename)

            try:

                df = pd.read_excel(uploaded_file, sheet_name=None)

                # Extract the first few rows of each sheet for preview
                preview_data = {sheet: data.head().to_dict() for sheet, data in df.items()}

                return JsonResponse({'status': 'success', 'preview_data': preview_data})
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
        else:
            return JsonResponse({'status': 'error', 'message': 'No file uploaded.'})
    # return render(request, 'userrequests/uploadexcel.html', {'uservalues': uservalues })



def optimize_model(request):
    request_id = request.POST.get("user_request_id")

    uservalues =  request.session.get('uservalues', None)
    if uservalues is None:
        messages.error(request, 'Session expired or invalid.')
        return redirect('login')
    
    user_key = UserKey.objects.get(user=uservalues['pk'])
    private_key = user_key.private_key
    all_requests = RequestModel.objects.all()
    user_requests = []

    for req in all_requests:
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(req.created_by))
            if decrypted_created_by == uservalues['email']:
                req.created_by = decrypted_created_by  # Optional: for display
                user_requests.append(req)
        except Exception as e:
            print("Decryption failed for a request:", e)

    if request.method == "POST":
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            print('this is file name', filename)
            print('fs location', fs.location)
            file_url = fs.url(filename)

                        # Run the Gurobi optimization logic
            try:
                # Assuming your Gurobi logic is in a separate function for reusability
                response = run_optimization(os.path.join(fs.location, filename), request, request_id)
                messages.success(request, 'Optimization ran successfully and the request has been created.')
                return response               
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
                print("Error during optimization:", e)
            
            

            # Redirect to the request history page after success
    
    return render(request, 'userrequests/requests_list_history.html', {
        'uservalues': uservalues, 
        'requests' : user_requests })

#Function that defines which nodes can be reached from each node within a given number of steps
def compute_reachability_matrix(nodes, arcs, max_steps):
    # Initialize reachability matrix and adjacency list
    reachability = defaultdict(lambda: defaultdict(int))
    adjacency_list = defaultdict(list)
    
    # Creating adjacency list from arcs
    for (i, j) in arcs:
        adjacency_list[i].append(j)
    
    # Compute Reachability Matrix using Breadth-First Search (BFS)
    for node in nodes:
        queue = deque([(node, 0)])
        reachability[node][node] = 0
        
        while queue:
            current_node, steps = queue.popleft()
            
            if steps < max_steps:
                for neighbor in adjacency_list[current_node]:
                    if neighbor not in reachability[node] or reachability[node][neighbor] > steps + 1:
                        reachability[node][neighbor] = steps + 1
                        queue.append((neighbor, steps + 1))
    
    return reachability


def run_optimization(file_name, request, request_id):
     # Extract request_id from file name
    # request_id = os.path.basename(file_name).split('_data')[0]
        # Create a new optimization model for SEFSCCP
    m = gp.Model("Sensor Placement Project")

    uservalues =  request.session.get('uservalues', None)

    if uservalues is None:
        messages.error(request,'Something went wrong, Cant Raise a request')
        return redirect('sensd')
    
    username = urlsafe_base64_encode(force_bytes(uservalues['username']))
    requested_date = uservalues.get('requested_date', datetime.now().strftime('%Y%m%d')) 
    new_result = ResultModel(
        user_request_id = request_id,  # Generate or assign a unique value
        created_by=request.user.email,  # Assuming user is authenticated
        updated_by=request.user.email,
        created_on=timezone.now(),
        updated_on=timezone.now(),
        is_deleted=False
    )
    new_result.save()
    
    new_result.user_result_id = f"Result-{request_id}{new_result.result_id}"
    new_result.save()

    # Sets and Parameters
    # Load All Excel Data
    # file_name = "Small Test Data.xlsx" #"Test Data.xlsx"
    all_nodes_sheet = "All Nodes"
    initial_nodes_sheet = "Initial Nodes"
    finished_products_sheet = "Finished Products"
    arcs_sheet = "Arcs"
    pathogen_testing_method_sheet = "Pathogen Testing Methods"
    pathogen_testing_method_f_node_sheet = "Pathogen Testing Methods F Node"
    dynamic_parameters_sheet = "Dynamic Parameters"

    # All Nodes Data Pull
    df_all_nodes = pd.read_excel(io=file_name, sheet_name=all_nodes_sheet)
    all_nodes = df_all_nodes["ID"].unique()
    probability = {}
    cum_cost = {}
    demand_rate = {}

    # Loop through nodes and populate dictionaries with node-specific data
    for a in all_nodes:
        all_nodes_data = df_all_nodes[df_all_nodes["ID"] == a]
        probability[a] = all_nodes_data["Probability"].values[0]
        cum_cost[a] = all_nodes_data["Cumulative Cost"].values[0]
        demand_rate[a] = all_nodes_data["Demand Rate"].values[0]

    # Initial/NoPredecessor Nodes Data Pull
    df_initial_nodes = pd.read_excel(io=file_name, sheet_name=initial_nodes_sheet)
    initial_nodes = df_initial_nodes["Node ID"].unique()

    # Finished Products Data Pull
    df_finished_products = pd.read_excel(io=file_name, sheet_name=finished_products_sheet)
    finished_products = df_finished_products["Node ID"].unique()

    # Arcs Data Pull
    df_arcs = pd.read_excel(io=file_name, sheet_name=arcs_sheet)
    arcs = [(row["From Node ID"], row["To Node ID"]) for idx, row in df_arcs.iterrows()]
    multiplier = {row["From Node ID"]: row["Multiplier"] for idx, row in df_arcs.iterrows()}
    # print(arcs)
    # Pathogen Testing Methods Data Pull
    df_pathogen_testing_methods = pd.read_excel(io=file_name, sheet_name=pathogen_testing_method_sheet)
    pathogen_testing_methods = df_pathogen_testing_methods["ID"].unique()

    # Pathogen Testing Methods For Nodes Data Pull
    df_pathogen_testing_methods_f_nodes = pd.read_excel(io=file_name, sheet_name=pathogen_testing_method_f_node_sheet)
    pathogen_testing_methods_f_nodes = df_pathogen_testing_methods_f_nodes["Pathogen Testing Method ID"].unique()
    sensitivity = {}
    direct_cost = {}
    lead_time = {}

    # Loop through nodes and pathogen testing method and populate dictionaries with node-specific data
    for idx, row in df_pathogen_testing_methods_f_nodes.iterrows():
        node = row["Node ID"]
        method = row["Pathogen Testing Method ID"]
        if node not in sensitivity:
            sensitivity[node] = {}
            direct_cost[node] = {}
            lead_time[node] = {}
        sensitivity[node][method] = row["Sensitivity"]
        direct_cost[node][method] = row["Direct Cost"]
        lead_time[node][method] = row["Lead Time"]

    # k = 3              # are these constants or will change 
    # B = 30000
    # alpha = 0.5
    df_dynamic_parameters = pd.read_excel(io=file_name, sheet_name=dynamic_parameters_sheet)
    k = df_dynamic_parameters["Max Steps (K)"].values[0]
    alpha = df_dynamic_parameters["Max Percentage (Alpha)"].values[0]
    B = df_dynamic_parameters["Max Budget (B)"].values[0]

    # Call function compute_reachability_matrix and pass the respective parameters for the dictionary reachability_matrix
    reachability_matrix = compute_reachability_matrix(all_nodes, arcs, k)
    # print("Reachability Matrix:")
    # for i in all_nodes:
    #     for j in all_nodes:
    #         if reachability_matrix[i][j] <= k:
    #             print(f"({i}, {j}): {reachability_matrix[i][j]}")
    # print(reachability_matrix)

    # Decision Variables
    y = m.addVars(all_nodes, vtype=GRB.BINARY, name="y") # Pathogen Testing
    z = m.addVars(all_nodes, vtype=GRB.BINARY, name="z") # Node Controllability
    x = m.addVars(all_nodes, pathogen_testing_methods_f_nodes, vtype=GRB.BINARY, name="x") # Testing Method Selection
    c = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="c") # Direct Cost
    l = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="l") # Lead Time
    s = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="s") # Sensitivity
    r = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="r") # Reliability
    ir = m.addVars(set(all_nodes) - set(initial_nodes), vtype=GRB.CONTINUOUS, name="ir") # Inbound Reliability
    w = m.addVar(vtype=GRB.CONTINUOUS, name="w") # System wide reliablity of safety
    
    # Objective Function
    m.setObjective(w, GRB.MAXIMIZE)

    # Constraints
    for i in all_nodes:
        m.addConstr(gp.quicksum(x[i, s] for s in pathogen_testing_methods_f_nodes) == y[i])
        m.addConstr(c[i] == gp.quicksum(direct_cost[i][s] * x[i, s] for s in pathogen_testing_methods_f_nodes))
        m.addConstr(l[i] == gp.quicksum(lead_time[i][s] * x[i, s] for s in pathogen_testing_methods_f_nodes))
        m.addConstr(s[i] == gp.quicksum(sensitivity[i][s] * x[i, s] for s in pathogen_testing_methods_f_nodes))

    # reachability_matrix[i].get(j, k+1) checks the reachability from node i to node j, returning a default value of k+1 if j is not a key in reachability_matrix[i]
    for j in all_nodes:
        m.addConstr(z[j] <= gp.quicksum(y[j] * (1 if reachability_matrix[i].get(j, k+1) <= k else 0) for i in all_nodes))

    m.addConstr(gp.quicksum(z[i] for i in all_nodes) >= alpha * len(all_nodes))

    m.addConstr(gp.quicksum(c[i] + cum_cost[i] * demand_rate[i] * l[i] for i in all_nodes) <= B)

    for i in initial_nodes:
        m.addConstr(r[i] == (1 - probability[i]) + s[i] * probability[i])

    for j in set(all_nodes) - set(initial_nodes):
        for (i, j_arc) in arcs:
            if j_arc == j:
                m.addConstr(ir[j] <= r[i])
                
    for i in set(all_nodes) - set(initial_nodes):
        m.addConstr(r[i] == ir[i] * ((1 - probability[i]) + s[i] * probability[i]))

    for i in finished_products:
        m.addConstr(w <= r[i])

    # Optimize model
    m.optimize()

    # Print the results
    if m.status == GRB.OPTIMAL:
        for i in all_nodes:
            sum_c = c[i].X
            sum_cumcost = cum_cost[i]
            sum_demand = demand_rate[i]
            sum_leadtime = l[i].X    

            print(f'Node {i}: {i}')
            print(f'  Direct Cost for Node [{i}]: {sum_c}')
            print(f'  Cumulative Cost for Node [{i}] : {sum_cumcost}')
            print(f'  Demand Rate for Node {i}: {sum_demand}')
            print(f'  Lead Time for Node {i}: {sum_leadtime}')

            NodeResult.objects.create(
                request_id = request_id,
                result_id = new_result.user_result_id,
                node_id=i,
                direct_cost=c[i].X,
                cumulative_cost=cum_cost[i],
                demand_rate=demand_rate[i],
                lead_time=l[i].X
            )

        for v in m.getVars():
            print(f'{v.varName}: {v.x}')

            VariableResult.objects.create(
                request_id = request_id,
                result_id = new_result.user_result_id,
                variable_name=v.varName,
                value=v.x
            )

        print(f'Objective Value: {m.objVal}')
    else:
        print('No optimal solution found')

    node_feilds = {
        'node_id': 'Node ID',
        'direct_cost':'Direct Cost for Node',
        'cumulative_cost':'Cumulative Cost for Node',
        'demand_rate':'Demand Rate for Node',
        'lead_time':'Lead Time for Node'
    }
    Variable_feilds = {
        'variable_name':'Variable Name',
        'value':'Value'
    }

    Nodes_list = NodeResult.objects.filter(result_id = new_result.user_result_id).values(*node_feilds.keys())
    Variables_list = VariableResult.objects.filter(result_id = new_result.user_result_id).values(*Variable_feilds.keys())

    
    
    print("this is nodes list", Nodes_list)

    output_file = f"media/excels/{request_id}_optimization_results.xlsx"

    # Create an in-memory BytesIO object
    output = BytesIO()
    
    # Create the Excel writer using the in-memory buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:  
        # Write DataFrame to Excel
        Node_feilds = {
        'node_id': 'Node ID',
        'direct_cost':'Direct Cost for Node',
        'cumulative_cost':'Cumulative Cost for Node',
        'demand_rate':'Demand Rate for Node',
        'lead_time':'Lead Time for Node'
        }
        Variable_feilds = {
        'y': 'Pathogen Testing',
        'z': 'Node Controllability',
        'x': 'Testing Method Selection',
        'c': 'Direct Cost',
        'l': 'Lead Time',
        's': 'Sensitivity',
        'r': 'Reliability',
        'ir': 'Inbound Reliability',
        'W': 'System-wide Reliability',
        'value':'Value'
        }

        def rename_variable(variable_name, Variable_fields):
            for key, value in Variable_fields.items():
                if re.match(rf'^{key}\[.*\]$', variable_name):
                    return variable_name.replace(key, value)
            return variable_name
    
        if Nodes_list:
            df_node_results = pd.DataFrame(list(Nodes_list))
            df_node_results.rename(columns=Node_feilds, inplace=True)
            df_node_results.to_excel(writer, sheet_name='Node Results', index=False)

        if Variables_list:
            df_variable_results = pd.DataFrame(list(Variables_list))
            # df_variable_results.rename(columns=Variable_feilds, inplace=True)
            df_variable_results['variable_name'] = df_variable_results['variable_name'].apply(lambda x: rename_variable(x, Variable_feilds))
            df_variable_results.to_excel(writer, sheet_name='Variable Results', index=False)

    # Make sure the BytesIO buffer is at the beginning
    output.seek(0)

    # Serve the file as an HTTP response for download
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={request_id}_optimization_results.xlsx'
    
    print("this is response", response)
    return response

   



def delete_request(request, requestid):
    # Get the request instance based on user_request_id (since request_id is a string)
    request_instance = get_object_or_404(RequestModel, user_request_id=requestid)

    # Delete related records
    AllNodes.objects.filter(user_request_id=requestid).delete()
    InitialNodes.objects.filter(user_request_id=requestid).delete()
    FinishedGoods.objects.filter(user_request_id=requestid).delete()
    Arc.objects.filter(user_request_id=requestid).delete()
    PathogenTestingMethod.objects.filter(user_request_id=requestid).delete()
    PathogenTestingMethodFNodes.objects.filter(user_request_id=requestid).delete()
    DynamicParameters.objects.filter(user_request_id=requestid).delete()

    # Delete the request itself
    request_instance.delete()

    messages.success(request, "Request and related records deleted successfully.")
    return redirect(request.META.get('HTTP_REFERER', '/'))

import json
from django.shortcuts import render
from .models import NodeResult, VariableResult

def generate_visualization(result_id):
    """
    Prepares structured data for tables (Node and Variable Results).
    """
    # Fetch data from models
    node_results = NodeResult.objects.filter(result_id=result_id)
    variable_results = VariableResult.objects.filter(result_id=result_id)

    # Node Fields and Labels
    node_field_labels = {
        "node_id": "Node ID",
        "direct_cost": "Direct Cost",
        "cumulative_cost": "Cumulative Cost",
        "demand_rate": "Demand Rate",
        "lead_time": "Lead Time"
    }

    # Variable Fields and Labels
    variable_labels = {
        'y': 'Pathogen Testing',
        'x': 'Testing Method Selection',
        'z': 'Node Controllability',
        'c': 'Direct Cost',
        'l': 'Lead Time',
        's': 'Sensitivity',
        'r': 'Reliability',
        'ir': 'Inbound Reliability',
        'w': 'System-wide Reliability'
    }

    # Prepare node data for table
    node_data = []
    for node in node_results:
        node_data.append({
            "Node ID": node.node_id,
            "Direct Cost": node.direct_cost,
            "Cumulative Cost": node.cumulative_cost,
            "Demand Rate": node.demand_rate,
            "Lead Time": node.lead_time
        })

    # Prepare variable data for table
    
    request_id = ResultModel.objects.get(user_result_id=result_id).user_request_id

    print("this is request id", request_id)

    variable_data = {}

    for var in variable_results:
        var_name = var.variable_name
        base_key = var_name.split('[')[0]
        label = variable_labels.get(base_key, base_key)
        values = re.findall(r'\d+', var_name)

        entry = {
            "Variable Name": label,
            "Value": var.value,
        }

        if len(values) == 1:
            try:
                node = AllNodes.objects.get(user_request_id=request_id, node_id=int(values[0]))
                entry["Node Name"] = node.node_name
            except AllNodes.DoesNotExist:
                entry["Node Name"] = ""
        elif len(values) == 2:
            try:
                node = AllNodes.objects.get(user_request_id=request_id, node_id=int(values[0]))
                ptm = PathogenTestingMethod.objects.get(user_request_id=request_id, ptm_id=int(values[1]))
                entry["Node Name"] = node.node_name
                entry["Pathogen Testing Method"] = ptm.pathogen_testing_method
            except Exception:
                entry["Node Name"] = entry.get("Node Name", "")
                entry["Pathogen Testing Method"] = entry.get("Pathogen Testing Method", "")

        if label not in variable_data:
            variable_data[label] = []

        variable_data[label].append(entry)
        

    return {
        "nodes": node_data,
        "variables": variable_data
    }


def view_results(request, result_id):
    """
    Renders the visualization page with structured table data.
    """
    table_data = generate_visualization(result_id)

    return render(request, 'userrequests/results_visualization.html', {
        "table_data": json.dumps(table_data),
        "result_id": result_id
    })

#This code is for saving the data from Excel to the Request Models # Test Code 

import pandas as pd
import uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import (
    Request, AllNodes, InitialNodes, FinishedGoods, Arc,
    PathogenTestingMethod, PathogenTestingMethodFNodes, DynamicParameters
)

def save_excel_data(request):
    if request.method == "POST" and request.FILES.get('file'):
        uploaded_file = request.FILES['file']

        # Generate a unique user_request_id
        user_request_id = str(uuid.uuid4())

        # Save the file to the "excels/" directory
        file_path = default_storage.save(f"excels/{uploaded_file.name}", ContentFile(uploaded_file.read()))

        uservalues =  request.session.get('uservalues', None)

        if uservalues is None:
            messages.error(request,'Something went wrong, Cant Raise a request')
            return redirect('sensd')

        # Create a new Request entry
        requested_date = uservalues.get('requested_date', datetime.now().strftime('%Y%m%d'))
        new_request = Request.objects.create(
            user_request_id=f"Request{requested_date}",
            final_excel=file_path,
            created_by=request.user.email,  # Assuming user is authenticated
            updated_by=request.user.email,
            created_on=timezone.now(),
            updated_on=timezone.now(),
            is_deleted=False
        )

        new_request.save()
    
        new_request.user_request_id = f"Request{requested_date}{new_request.request_id}"
        new_request.save()
        
        request.session['latest_request_id'] = new_request.user_request_id
        user_request_id = new_request.user_request_id
        try:
            # Load Excel file
            excel_data = pd.ExcelFile(uploaded_file)

            # Save AllNodes data
            if "All Nodes" in excel_data.sheet_names:
                df_nodes = pd.read_excel(excel_data, sheet_name="All Nodes")
                all_nodes_objects = [
                    AllNodes(
                        user_request_id=user_request_id,
                        node_id=row['ID'],
                        node_name=row['Node Name'],
                        probability=row['Probability'],
                        cumulative_cost=row['Cumulative Cost'],
                        demand_rate=row['Demand Rate'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_nodes.iterrows()
                ]
                AllNodes.objects.bulk_create(all_nodes_objects)

            # Save InitialNodes data
            if "Initial Nodes" in excel_data.sheet_names:
                df_initial = pd.read_excel(excel_data, sheet_name="Initial Nodes")
                initial_nodes_objects = [
                    InitialNodes(
                        user_request_id=user_request_id,
                        node_id=row['Node ID'],
                        node_name=row['Node Name'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_initial.iterrows()
                ]
                InitialNodes.objects.bulk_create(initial_nodes_objects)

            # Save FinishedGoods data
            if "Finished Products" in excel_data.sheet_names:
                df_goods = pd.read_excel(excel_data, sheet_name="Finished Products")
                finished_goods_objects = [
                    FinishedGoods(
                        user_request_id=user_request_id,
                        node_id=row['Node ID'],
                        node_name=row['Node Name'],
                        demand_rate=row['Demand Rate'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_goods.iterrows()
                ]
                FinishedGoods.objects.bulk_create(finished_goods_objects)

            # Save Arc data
            if "Arcs" in excel_data.sheet_names:
                df_arcs = pd.read_excel(excel_data, sheet_name="Arcs")
                arc_objects = [
                    Arc(
                        user_request_id=user_request_id,
                        Arc_id=row['ID'],
                        from_node_id=row['From Node ID'],
                        from_node_name=row['From Node Name'],
                        to_node_id=row['To Node ID'],
                        to_node_name=row['To Node Name'],
                        multiplier=row['Multiplier'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_arcs.iterrows()
                ]
                Arc.objects.bulk_create(arc_objects)

            # Save PathogenTestingMethod data
            if "Pathogen Testing Methods" in excel_data.sheet_names:
                df_pathogen = pd.read_excel(excel_data, sheet_name="Pathogen Testing Methods")
                pathogen_objects = [
                    PathogenTestingMethod(
                        user_request_id=user_request_id,
                        ptm_id=row['ID'],
                        pathogen_testing_method=row['Pathogen Testing Methods'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_pathogen.iterrows()
                ]
                PathogenTestingMethod.objects.bulk_create(pathogen_objects)

            # Save PathogenTestingMethodFNodes data
            if "Pathogen Testing Methods F Node" in excel_data.sheet_names:
                df_ptm_fnodes = pd.read_excel(excel_data, sheet_name="Pathogen Testing Methods F Node")
                ptm_fnode_objects = [
                    PathogenTestingMethodFNodes(
                        user_request_id=user_request_id,
                        node_id=row['Node ID'],
                        pathogen_testing_method_id=row['Pathogen Testing Method ID'],
                        sensitivity=row['Sensitivity'],
                        direct_cost=row['Direct Cost'],
                        lead_time=row['Lead Time'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_ptm_fnodes.iterrows()
                ]
                PathogenTestingMethodFNodes.objects.bulk_create(ptm_fnode_objects)

            # Save DynamicParameters data
            if "Dynamic Parameters" in excel_data.sheet_names:
                df_dynamic = pd.read_excel(excel_data, sheet_name="Dynamic Parameters")
                dynamic_parameters_objects = [
                    DynamicParameters(
                        user_request_id=user_request_id,
                        dynamic_parameter_id=row['ID'],
                        maxsteps_k=row['Max Steps (K)'],
                        maxpercentage_alpha=row['Max Percentage (Alpha)'],
                        maxbudget_B=row['Max Budget (B)'],
                        created_by=request.user.email if request.user.is_authenticated else "Anonymous"
                    )
                    for _, row in df_dynamic.iterrows()
                ]
                DynamicParameters.objects.bulk_create(dynamic_parameters_objects)

            return JsonResponse({"status": "success", "message": "Data saved successfully", "user_request_id": user_request_id})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request", "user_request_id": user_request_id })


def run_optimization_from_db(request, requestid):
    # 1. Get data from DB
    all_nodes_qs = AllNodes.objects.filter(user_request_id=requestid)
    initial_nodes_qs = InitialNodes.objects.filter(user_request_id=requestid)
    finished_goods_qs = FinishedGoods.objects.filter(user_request_id=requestid)
    arcs_qs = Arc.objects.filter(user_request_id=requestid)
    ptm = PathogenTestingMethod.objects.filter(user_request_id=requestid)
    ptm_fnodes_qs = PathogenTestingMethodFNodes.objects.filter(user_request_id=requestid)
    dyn_params = DynamicParameters.objects.get(user_request_id=requestid)

    all_nodes = [n.node_id for n in all_nodes_qs]
    initial_nodes = [n.node_id for n in initial_nodes_qs]
    finished_products = [n.node_id for n in finished_goods_qs]
    arcs = [(a.from_node_id, a.to_node_id) for a in arcs_qs]
    ptm_ids = list(set(int(float(p.pathogen_testing_method_id)) for p in ptm_fnodes_qs))



    probability = {n.node_id: n.probability for n in all_nodes_qs}
    cum_cost = {n.node_id: n.cumulative_cost for n in all_nodes_qs}
    demand_rate = {n.node_id: n.demand_rate for n in all_nodes_qs}

    sensitivity = defaultdict(dict)
    direct_cost = defaultdict(dict)
    lead_time = defaultdict(dict)
    for p in ptm_fnodes_qs:
        i = p.node_id
        j = int(float(p.pathogen_testing_method_id))  # 🔥 enforce integer here
        sensitivity[i][j] = p.sensitivity
        direct_cost[i][j] = p.direct_cost
        lead_time[i][j] = p.lead_time

    k = dyn_params.maxsteps_k
    alpha = dyn_params.maxpercentage_alpha
    B = dyn_params.maxbudget_B

    reachability = compute_reachability_matrix(all_nodes, arcs, k)

    # 2. Create ResultModel entry
    new_result = ResultModel.objects.create(
        user_request_id=requestid,
        created_by=request.user.email,
        updated_by=request.user.email,
        created_on=timezone.now(),
        updated_on=timezone.now(),
        is_deleted=False
    )
    new_result.user_result_id = f"Result-{requestid}{new_result.result_id}"
    new_result.save()

    # 3. Gurobi Model
    m = gp.Model("Sensor_Placement")

    y = m.addVars(all_nodes, vtype=GRB.BINARY, name="y")
    z = m.addVars(all_nodes, vtype=GRB.BINARY, name="z")
    x = m.addVars(all_nodes, ptm_ids, vtype=GRB.BINARY, name="x")
    c = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="c")
    l = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="l")
    s = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="s")
    r = m.addVars(all_nodes, vtype=GRB.CONTINUOUS, name="r")
    ir = m.addVars(set(all_nodes) - set(initial_nodes), vtype=GRB.CONTINUOUS, name="ir")
    w = m.addVar(vtype=GRB.CONTINUOUS, name="w")

    m.setObjective(w, GRB.MAXIMIZE)

    for i in all_nodes:
        m.addConstr(gp.quicksum(x[i, j] for j in ptm_ids) == y[i])
        m.addConstr(c[i] == gp.quicksum(direct_cost[i].get(j, 0) * x[i, j] for j in ptm_ids))
        m.addConstr(l[i] == gp.quicksum(lead_time[i].get(j, 0) * x[i, j] for j in ptm_ids))
        m.addConstr(s[i] == gp.quicksum(sensitivity[i].get(j, 0) * x[i, j] for j in ptm_ids))

    for j in all_nodes:
        m.addConstr(z[j] <= gp.quicksum(y[i] * (1 if reachability[i].get(j, k + 1) <= k else 0) for i in all_nodes))

    m.addConstr(gp.quicksum(z[i] for i in all_nodes) >= alpha * len(all_nodes))
    m.addConstr(gp.quicksum(c[i] + cum_cost[i] * demand_rate[i] * l[i] for i in all_nodes) <= B)

    for i in initial_nodes:
        m.addConstr(r[i] == (1 - probability[i]) + s[i] * probability[i])

    for (i, j) in arcs:
        if j in ir:
            m.addConstr(ir[j] <= r[i])

    for i in set(all_nodes) - set(initial_nodes):
        m.addConstr(r[i] == ir[i] * ((1 - probability[i]) + s[i] * probability[i]))

    for i in finished_products:
        m.addConstr(w <= r[i])

    m.optimize()

    # 4. Save results
    for i in all_nodes:
        NodeResult.objects.create(
            request_id=requestid,
            result_id=new_result.user_result_id,
            node_id=i,
            direct_cost=c[i].X,
            cumulative_cost=cum_cost[i],
            demand_rate=demand_rate[i],
            lead_time=l[i].X
        )

    for var in m.getVars():
        VariableResult.objects.create(
            request_id=requestid,
            result_id=new_result.user_result_id,
            variable_name=var.varName,
            value=var.X
        )

    return redirect(reverse("view_results", kwargs={"result_id": new_result.user_result_id}))
