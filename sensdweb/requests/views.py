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

from .models import Request as RequestModel, AllNodes, InitialNodes, FinishedGoods, Arc, PathogenTestingMethod , PathogenTestingMethodFNodes
from .forms import AllNodeForm, InitialNodeForm, FinishedGoodsForm, ArcForm, PathogenTestingMethodForm , PathogenTestingMethodFNodesForm

from django.core.files.storage import FileSystemStorage

import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from collections import defaultdict, deque #Used to create dictionaries with default values and double-ended queues
# Create your views here.

def newRequest(request):
    uservalues =  request.session.get('uservalues', None)

    if uservalues is None:
        messages.error(request,'Something went wrong, Cant Raise a request')
        return redirect('sensd')
    
    username = urlsafe_base64_encode(force_bytes(uservalues['username']))
    new_request = RequestModel(
        user_request_id = f"Req{uservalues['pk']}{username}",  # Generate or assign a unique value
        created_by=request.user.email,  # Assuming user is authenticated
        updated_by=request.user.email,
        created_on=timezone.now(),
        updated_on=timezone.now(),
        is_deleted=False
    )
    new_request.save()
    
    new_request.user_request_id = f"Req{uservalues['pk']}{username}{new_request.request_id}"
    new_request.save()

    messages.success(request, 'New Request Initiated')
    return redirect(reverse('AllNodes', kwargs={'requestid': new_request.user_request_id}))
    
    
    
def allNodes(request, requestid):
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

    print("this is pk", pk)
    print("this is requestid", request.body)
    Model = request.POST.get('Model')
    ModelForm = request.POST.get('ModelForm')
    node = get_object_or_404(Model, id=pk, user_request_id=requestid)
    if request.method == 'POST':
        form = ModelForm(request.POST , instance=node)
        if form.is_valid():
            # Update the object with form data
            node = form.save(commit=False)
            node.updated_by = request.user.email  # Set the user who updated this
            node.save()  # Save the updated object to the database
            
            # Redirect to the same page or any other page
            return redirect('AllNodes', requestid=requestid)
    else:
        form = ModelForm(instance=node)
    # Retrieve all nodes associated with the request ID
    nodes = Model.objects.filter(user_request_id=requestid, is_deleted=False)
    
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
    
    return render(request, 'userrequests/pathogen_testing_method_fnodes.html', {'uservalues': uservalues, 'formset': ptm_fnode_form_set, 'pathogen_testing_method_fnodes': ptmFNodeValues, 'requestid': requestid })

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
    
    # Collect data from each model and rename columns
    all_nodes = AllNodes.objects.filter(user_request_id=user_request_id).values(*all_nodes_fields.keys())
    initial_nodes = InitialNodes.objects.filter(user_request_id=user_request_id).values(*initial_nodes_fields.keys())
    finished_goods = FinishedGoods.objects.filter(user_request_id=user_request_id).values(*finished_goods_fields.keys())
    arcs = Arc.objects.filter(user_request_id=user_request_id).values(*arcs_fields.keys())
    pathogen_testing_methods = PathogenTestingMethod.objects.filter(user_request_id=user_request_id).values(*ptm_fields.keys())
    pathogen_testing_method_f_nodes = PathogenTestingMethodFNodes.objects.filter(user_request_id=user_request_id).values(*ptm_f_nodes_fields.keys())
    
    # Create a Pandas Excel writer using Openpyxl
    output_file_path = f"media/excels/{user_request_id}_data.xlsx"
    writer = pd.ExcelWriter(output_file_path, engine='openpyxl')
    
    # Convert QuerySets to DataFrames and rename columns
    if all_nodes:
        all_nodes_df = pd.DataFrame(list(all_nodes))
        all_nodes_df.rename(columns=all_nodes_fields, inplace=True)
        all_nodes_df.to_excel(writer, sheet_name='All Nodes', index=False)
    
    if initial_nodes:
        initial_nodes_df = pd.DataFrame(list(initial_nodes))
        initial_nodes_df.rename(columns=initial_nodes_fields, inplace=True)
        initial_nodes_df.to_excel(writer, sheet_name='Initial Nodes', index=False)
    
    if finished_goods:
        finished_goods_df = pd.DataFrame(list(finished_goods))
        finished_goods_df.rename(columns=finished_goods_fields, inplace=True)
        finished_goods_df.to_excel(writer, sheet_name='Finished Products', index=False)
    
    if arcs:
        arcs_df = pd.DataFrame(list(arcs))
        arcs_df.rename(columns=arcs_fields, inplace=True)
        arcs_df.to_excel(writer, sheet_name='Arcs', index=False)
    
    if pathogen_testing_methods:
        ptm_df = pd.DataFrame(list(pathogen_testing_methods))
        ptm_df.rename(columns=ptm_fields, inplace=True)
        ptm_df.to_excel(writer, sheet_name='Pathogen Testing Methods', index=False)
    
    if pathogen_testing_method_f_nodes:
        ptm_f_nodes_df = pd.DataFrame(list(pathogen_testing_method_f_nodes))
        ptm_f_nodes_df.rename(columns=ptm_f_nodes_fields, inplace=True)
        ptm_f_nodes_df.to_excel(writer, sheet_name='Pathogen Testing Methods F Node', index=False)
    
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

    requestlists = RequestModel.objects.filter(created_by = uservalues['email'])
    return render(request, 'userrequests/requests_list_history.html', {'uservalues': uservalues, 'requests' : requestlists })

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

    return render(request, 'userrequests/uploadexcel.html', {'uservalues': uservalues })



def optimize_model(request):
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
                run_optimization(os.path.join(fs.location, filename))
                messages.success(request, 'Optimization ran successfully and the request has been created.')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')

            return redirect('user_requests')  # Redirect to the request history page after success
    
    return render(request, 'userrequests/requests_list_history.html')

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


def run_optimization(file_name):
        # Create a new optimization model for SEFSCCP
    m = gp.Model("Sensor Placement Project")

    # Sets and Parameters
    # Load All Excel Data
    # file_name = "Small Test Data.xlsx" #"Test Data.xlsx"
    all_nodes_sheet = "All Nodes"
    initial_nodes_sheet = "Initial Nodes"
    finished_products_sheet = "Finished Products"
    arcs_sheet = "Arcs"
    pathogen_testing_method_sheet = "Pathogen Testing Methods"
    pathogen_testing_method_f_node_sheet = "Pathogen Testing Methods F Node"

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

    k = 3              # are these constants or will change 
    B = 30000
    alpha = 0.5

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

            print(f'Node {i}:')
            print(f'  Direct Cost for node [{i}]: {sum_c}')
            print(f'  Cumulative Cost for node [{i}] : {sum_cumcost}')
            print(f'  Demand Rate for node {i}: {sum_demand}')
            print(f'  Lead Time for node {i}: {sum_leadtime}')

        for v in m.getVars():
            print(f'{v.varName}: {v.x}')

        print(f'Objective Value: {m.objVal}')
    else:
        print('No optimal solution found')