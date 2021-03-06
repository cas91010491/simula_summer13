import numpy as np
import pylab
import os, sys
np.set_printoptions(threshold=np.nan)
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
from monodomain_solver import Monodomain_solver, Time_solver, Goss_wrapper
from extracellular_solver import Extracellular_solver
from torso_solver import Torso_solver
from dolfin_animation_tools import numpyfy, mcrtmv

from gotran import load_ode
from dolfin import *
from goss import *

def stimulation_domain(C, amp=-10):
	m = C.shape[0]
	ist = np.zeros(m);
	for i in range(m):
		x, y = C[i,:]
		#if np.sqrt(((y-0.5)**2+x**2))<0.1:
		if np.sqrt(((y-0.5)**2+(x-0.5)**2))<0.1:
			ist[i] = amp

	return ist

def make_parameter_field(coor, ode, **parameters):

    parameter_names = ode.get_field_parameter_names()
    nop = len(parameter_names)
    if isinstance(coor, (int, float)):
		m = coor
		print " Only the number of coordinates are given, not the actual coordinates.\n That is OK as long as there are no function to evalute in the parameters list."
    else:
		m = coor.shape[0]
	
    P = np.zeros((m,nop))
    # set default values in case they are not sent in
    for i in range(nop):
		P[:,i] = ode.get_parameter(parameter_names[i])
	
    for name, value in parameters.iteritems(): 
		found = False
		for i in range(nop):
			if parameter_names[i] != name:
				continue
			if hasattr(value, '__call__'):
				print "setting with function: ", i, name
				for j in range(m):
					P[j,i] = value(coor[j,:])
			elif isinstance(value, (int, float)):
				print "setting with constant: ", i, name, value
				P[:,i] = value
			else:
				print "setting with table: ", i, name
				for j in range(m):
					P[j,i] = value[j]
			found = True
	
		if not found:
			print "Warning: given parameter does not exist in this model:", name
	
    return P

def advance(self, u, t, dt):
	assert(isinstance(u, Function))
	goss_solver = self.goss_solver
	dof_temp_values = u.vector().array()
	goss_solver.get_field_states(self.vertex_temp_values)
	self.vertex_temp_values[self.vertex_to_dof_map] = dof_temp_values
	goss_solver.set_field_states(self.vertex_temp_values)


	if t<5:
		goss_solver.set_field_parameters(P1)
	else:
		goss_solver.set_field_parameters(P0)

	goss_solver.forward(t, dt)

	goss_solver.get_field_states(self.vertex_temp_values)
	dof_temp_values[:] = self.vertex_temp_values[self.vertex_to_dof_map]
	u.vector().set_local(dof_temp_values)
	u.vector().apply('insert')
	return u

class Inner_box(SubDomain):
	def inside(self, x, on_boundary):
		eps = 1e-6
		return between(x[0], (0-eps, 1+eps)) and between(x[1], (0-eps, 1+eps)) and on_boundary

if __name__ == '__main__':
	### Parameters
	x_nodes, y_nodes = 49, 49 ## no. of nodes in each dir
	N = (x_nodes+1)*(y_nodes+1)
	T = 100
	dt = 0.5
	t = 0
	time_steps = int((T-t)/dt)
	time_solution_method = 'BE' ### crank nico

	save = False #save solutions as binary
	savemovie = False #create movie from results. Takes time! 
	plot_realtime = True

	# small hack
	mesh = UnitSquareMesh(x_nodes, y_nodes) 
	space = FunctionSpace(mesh, 'Lagrange', 1)
	### Setting up Goss/Gotran part
	ode = jit(load_ode("myocyte.ode"))
	vertex_to_dof_map =  space.dofmap().vertex_to_dof_map(mesh)
	N_thread = mesh.coordinates().shape[0]
	print vertex_to_dof_map.shape, mesh.coordinates().shape
	   
	ist = np.zeros(N_thread, dtype=np.float_) 
	ist = stimulation_domain(mesh.coordinates(), amp= -10)

	P0 = make_parameter_field(mesh.coordinates(), ode)
	P1 = make_parameter_field(mesh.coordinates(), ode, ist=ist) 

	ind_stim = P1[:,1]!=0
	print "P0", P0[P0[:,1]!=0.,1]
	print "P1", P1[ind_stim,1]

	solver = GRL2()
	ode_solver = ODESystemSolver(int(N_thread), solver, ode)
	#ode_solver.set_num_threads(3)
	### put the ode solver inside wrapper
	goss_wrap = Goss_wrapper(ode_solver, advance, space)

	#dump(ist.reshape(n,n), "ist", mn = -1, mx = 2)
	init_state = np.zeros(N_thread) # The solution vector
	#print mesh.coordinates().shape
	#asdkaspodkasp
	ode_solver.get_field_states(init_state)
	
	### Setting up FEniCS part: 
	solver = Monodomain_solver(dt=dt)
	solver.set_source_term(goss_wrap)
	method = Time_solver(time_solution_method)
	solver.set_geometry([x_nodes,y_nodes])
	solver.set_time_solver_method(method);



	print vertex_to_dof_map.shape, init_state.shape, mesh.coordinates().shape, max(vertex_to_dof_map)

	fenics_ordered_init_state = init_state[vertex_to_dof_map]
	solver.set_initial_condition(fenics_ordered_init_state);
	solver.set_boundary_conditions();

	### setting up isotropic M
	M00 = Constant('1e-4')
	M01 = Constant('0.0')
	M10 = Constant('0.0')
	M11 = Constant('1e-4')
	M = ((M00, M01),(M10,M11))
	solver.set_M(M) # isotropic

	solver.set_form()
	for i in range(110):
		solver.solve_for_time_step()

	plot(solver.v_n)

	bidomain_elliptic = Extracellular_solver()
	bidomain_elliptic.set_geometry(mesh)
	bidomain_elliptic.set_v(solver.v_p.vector().array())
	bidomain_elliptic.set_M(M,M)
	bidomain_elliptic.set_form()
	bidomain_elliptic.solve_for_u()
	plot(bidomain_elliptic.u_n)

	torso_geometry = Rectangle(-1,-1, 2,2) - Rectangle(0,0,1,1)
	torso = Mesh(torso_geometry, 50)
	#plot(torso)
	torso_coordinates = torso.coordinates()
	eps = 1e-6

	#interactive()

	torso_boundary_function = MeshFunction('size_t', torso, 1)
	torso_boundary_function.set_all(0)

	# Initialize sub-domain instances
	inner_box = Inner_box()
	inner_box.mark(torso_boundary_function,1)


	### hack to assign the meshfunction to vertex values:
	dim = 2
	values = torso_boundary_function.array()
	#torso.init(dim)
	vertices = type(torso_boundary_function)(torso, 0)
	vertex_values = vertices.array()
	vertex_values[:] = 0
	con20 = torso.topology()(1,0)

	for facet in xrange(torso.num_edges()):
	  if values[facet]:
	    vertex_values[con20(facet)] = values[facet]

	V = FunctionSpace(torso, 'CG', 1)
	vertices.set_values(vertex_values)

	plot(vertices)


	# for i in [left,top,right,bottom]:
	# 	i.mark(torso_boundary_function, 1)

	#plot(torso_boundary_function)	
	#interactive()


	v = Function(V)
	v_array = v.vector().array()
	torso_bc_vec = vertices.array()
	idx = np.argwhere(torso_bc_vec == 1)
	
	heart_coordinates = bidomain_elliptic.mesh.coordinates()
	heart_vertex_to_dof_map = solver.V.dofmap().vertex_to_dof_map(solver.V.mesh())
	heart_coordinates = heart_coordinates[heart_vertex_to_dof_map]
	torso_vertex_to_dof_map = V.dofmap().vertex_to_dof_map(V.mesh())
	heart_solution_array = bidomain_elliptic.u_n.vector().array()


	for i in idx:
		diff = heart_coordinates - torso_coordinates[i]
		diff_floats = np.sum(diff**2,axis=1)
		min_index = np.argmin(diff_floats)
		value = heart_solution_array[min_index]
		v_array[i] = value


	#v_array[idx[:,0]] = 1.
	# new_array = np.zeros(v_array.shape[0], dtype='float_')
	# new_array[idx[:,0]] = 1.

	v_array = v_array[torso_vertex_to_dof_map]

	v.vector().set_local(v_array)
	# plot(v)
	# interactive()
	torso_mesh_boundary_marker_function = MeshFunction('size_t', torso, 1)
	torso_mesh_boundary_marker_function.set_all(0)
	inner_box.mark(torso_mesh_boundary_marker_function,1)
	torso_bcs = DirichletBC(V, v, torso_mesh_boundary_marker_function,1)#, method='pointwise')

	torso_solver = Torso_solver()
	torso_solver.set_geometry(torso)
	torso_solver.set_M(M)
	torso_solver.set_bcs(torso_bcs)
	torso_solver.set_form()
	torso_solver.solve_for_u()

	plot(torso_solver.u_n)
	interactive()

	# solver.solve(T, savenumpy=False, plot_realtime=True)

	# if save:
	# 	mcrtmv(int(solver.n_steps), \
	# 		0.01, \
	# 		solver.mesh, \
	# 		[x_nodes,y_nodes], \
	# 		solver.vertex_to_dof_map, \
	# 		savemovie=savemovie, \
	# 		mvname='test', \
	# 		vmin=-80, \
	# 		vmax=10)
	


