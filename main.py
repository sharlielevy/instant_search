
import webapp2

from google.cloud import datastore
from google.appengine.ext import ndb


# Creating Entities && Deleting Entities in the Cloud Datastore
def add_task(client, kind_type, attr_name , attr_val,attr_prev_val ):
    key = client.key(kind_type)
    task = datastore.Entity(key)
    task.update({
        'attribute_name': attr_name,
        'attribute_value': attr_val,
        'attribute_prev_value': attr_prev_val
    })
    client.put(task)
    return task.key
	a =1

def delete_task(client,kind_type, task_id):
    key = client.key(kind_type, task_id)
    client.delete(key)
    a =1

	
class Singleton:
    def __init__(self,decorated):
         self._decorated = decorated
    def Instance(self):
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance
    def __call__(self):
        raise TypeError("Singletone must be accessed thotough `Instance()`.")

    def __instancecheck__(self,inst):
        return isinstance(inst,self._decorated)

#Represent each set query that was given by the user
class Command:

    def __init__(self,ap_data,attr_name,attr_val,attr_prev_val) :
        self.app_data = ap_data
        self.attribute_name = attr_name
        self.attribute_prev_value = attr_prev_val
        self.attribute_value = attr_val
		
    def execute(self):
        self.app_data[self.attribute_name] = self.attribute_value;
  
    def undo(self):
        self.app_data[self.attribute_name] = self.attribute_prev_value;


#History manages two lists that holds the undo's and redo's commands.
#Cloud database reflects as well those two lists 
class History:
	def __init__(self) :
		self.undos = []
		self.redos = []
		

	def push_undo(self, cmd):
		self.undos.insert(len(self.undos),cmd)
		cmd.key = add_task(self.client,'UndoTask', cmd.attribute_name , cmd.attribute_value,cmd.attribute_prev_value)	
		
	def pop_undo(self):
		#RETURN THE RETRIEVED LAST INSETED ENTITY && REMOVE ENTITY FROM UNDO's Kind
		cmd  =   self.undos.pop(len(self.undos))
		delete_task(self.client,'UndoTask',cmd.key)
		return cmd

	def push_redo(self,cmd):
		self.redos.insert(len(self.redos),cmd)
		add_task(self.client, 'RedoTask',cmd.attribute_name , cmd.attribute_value,cmd.attribute_prev_value)	

	def pop_redo(self):
		cmd = self.redos.pop(len(self.redos))
		delete_task(self.client, 'RedoTask',cmd.key)
		return cmd

	def clear_redos(self):
		for item in self.redos:
		  client.delete(self.redos[item].key)
		self.redos = []

	def clear_undos(self):
		#REMOVE aALL ENTITY FROM UNDO's Kind
		for item in self.undos:
		   client.delete(self.undos[item].key)
		self.undos = []

	# 1. History write object to UNDO's Table
	# 2. History calls Command execute action is being called :
	#           - update the app attributes values)
	# 3. History clears REDO's Table	
	def execute(self, cmd):
		cmd.execute()
		self.push_undo(cmd)
		self.clear_redos()

    #1. History calls undo function that :
            # - pops out the last record of the UNDO's table.
            # - calls command undo function
    #2. History writes  the command into the REDO's table
	def undo(self):
		cmd = self.pop_undo()
		if cmd != None:
			cmd.undo()
			self.push_redo(cmd)
		return cmd
	#1. History calls redo function that :
            # - pops out the last record of the REDO's table.
            # - creating a new command out of the record values(name,value,prev_val)
            # - calls command redo function
    #2. History writes  the command into the UNDO's table	
	def redo(self):
		cmd = self.pop_redo()
		if cmd != None:
			cmd.execute()
			self.push_undo(cmd)
		return cmd
	def clear(self):
		self.clear_redos()
		self.clear_undos()


@Singleton
class DBHandler:
    #Set the variable variable_name to the value variable_value, neither variable names nor values
    #will contain spaces. Print the variable name and value after the change.
    def SetHandler(self, variable_name, variable_value):
        #1.Removing the spaces from the attribute_name strings
        variable_name.strip()
        variable_value = int(variable_value)
        prev_val = 0
        is_exist = variable_name in self.app_data
        if is_exist == True:
            prev_val =self.app_data[variable_name]

		# 2. Creating a new DB record with the name and value and call History.execute with the new object
        cmd = Command(self.app_data,variable_name,variable_value,prev_val)
        self.history.execute(cmd)

        #3. Print the variable name and value after the change
        response  = variable_name + "=" + str(variable_value)
        return response

    def UnsetHandler(self, variable_name):
        #1.Removing the spaces from the attribute_name && attribute values strings
        variable_value = "None"
        prev_val = 0
        is_exist = variable_name in self.app_data
        if is_exist == True:
            prev_val =self.app_data[variable_name]
        # 2. Creating a new DB record with the name and value and call History.execute with the new object
        cmd = Command(self.app_data,variable_name,0,prev_val)
        self.history.execute(cmd)

        #3. Print the variable name and value after the change
        response  = variable_name + "= None"
        return response
        
    def GetHandler(self, variable_name):
        #1.Removing the spaces from the attribute_name
        #2.Rerieve last value of the same attribute_name from UNDO's DB
        #3.Printing new varaible name and value to console
        # 
        variable_name.strip()
        ret_val = "None"
        is_exist = variable_name in self.app_data
        if is_exist == True:
            ret_val = self.app_data[variable_name]
        
        #3. Print the variable name and value after the change
        response  = variable_name + "=" + str(ret_val)
        return response
      

   
    # Req    
    #If no variables equal that value, print 0.
    def NumEqualToHandler(self,variable_value):
        count = 0
        #1.Querying  UNDO's list for all records that their attribute value is "variable_value"
        for item in self.app_data:
            if self.app_data[item] == variable_value:
                count += 1
       #2.Printing number of records. if therre is none, Print 0
        res = str(count)
        return res
   
    # Req   
    #  the original commands should be undone in the reverse order of their execution. 
    #  Print the name and value of the changed variable (after the undo) if successful, 
    #  or print NO COMMANDS if no commands may be undone.
    # Example: If you set the variable name x to the value 13 via request, then you set the variable name x to
    #  the value 22 via request, the undo request will undo the assignment of the value 22 to the variable x and
    def UndoHandler(self):
        cmd = self.history.undo()

        if cmd is None:
          res = "NO COMMANDS"
        else:
          res = cmd.attribute_name + "=" + cmd.attribute_value.str()

        return res

    # Req
     # the original commands should be redone in the original order of their execution.
     #  If another command was issued after an UNDO, the REDO command should do nothing.
     #   Print the name and value of the changed variable (after the redo) if successful, 
     #   or print NO COMMANDS if no commands may be re-done.
    def RedoHandler(self):
      cmd = self.history.redo()
      if cmd is None:
        res = "NO COMMANDS"
      else:
        res = cmd.attribute_name + "=" + cmd.attribute_value
      return res

   
    # Req
    # Exit the program. Your program will always receive this as its last command. You need to remove all your data 
    # from the application (clean all the Datastore entities). Print CLEANED when done.
    def EndHandler(self):
        #1.History will go over all REDO'S/UNDO'S tables clean it
        self.history.clear()
        
        #2.History will print out CLEANED to the console
        return "CLEANED"

	def create_client(project_id): 
		return datastore.Client(project_id) 


db_handler = DBHandler.Instance()
db_handler.app_data = {}
db_handler.history = History()
#google project id
db_handler.history.client = create_client(google_project_id)

class GetHandler(webapp2.RequestHandler):
    def get(self):
        res = db_handler.GetHandler(self.request.get('name'))
        self.response.out.write(res)

class SetHandler(webapp2.RequestHandler):
    def get(self):
       res = db_handler.SetHandler(self.request.get('name'),self.request.get('value'))
       self.response.out.write(res)

class UnsetHandler(webapp2.RequestHandler):
    def get(self):
        res = db_handler.UnsetHandler(self.request.get('name'))
        self.response.out.write(res)

class NumEqualToHandler(webapp2.RequestHandler):
    def get(self):
        res =db_handler.NumEqualToHandler(self.request.get('value'))
        self.response.out.write(res)

class UndoHandler(webapp2.RequestHandler):
    def get(self):
        res =db_handler.UndoHandler()
        self.response.out.write(res)

class RedoHandler(webapp2.RequestHandler):
    def get(self):
        res =db_handler.RedoHandler()
        self.response.out.write(res)

class EndHandler(webapp2.RequestHandler):
    def get(self):
        res =db_handler.EndHandler()
        self.response.out.write(res)



def main():
	application  = webapp2.WSGIApplication([
	    ('/get',	GetHandler),
		('/set', 	SetHandler),
        ('/unset',  UnsetHandler),
        ('/numequalto', NumEqualToHandler),
        ('/undo', 	 UndoHandler),
        ('/redo', 	 RedoHandler),
        ('/end',    EndHandler)    	
	], debug=True)
	application .run()

if __name__ == "__main__":
    main()
	
