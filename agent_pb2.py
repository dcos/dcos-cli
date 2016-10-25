# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: agent.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import mesos_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='agent.proto',
  package='mesos.agent',
  serialized_pb=_b('\n\x0b\x61gent.proto\x12\x0bmesos.agent\x1a\x0bmesos.proto\"\xa9\x06\n\x04\x43\x61ll\x12W\n\x1flaunch_nested_container_session\x18\t \x01(\x0b\x32..mesos.agent.Call.LaunchNestedContainerSession\x12H\n\x17\x61ttach_container_output\x18\n \x01(\x0b\x32\'.mesos.agent.Call.AttachContainerOutput\x12\x46\n\x16\x61ttach_container_input\x18\x0b \x01(\x0b\x32&.mesos.agent.Call.AttachContainerInput\x1a\xa4\x01\n\x1cLaunchNestedContainerSession\x12(\n\x0c\x63ontainer_id\x18\x01 \x02(\x0b\x32\x12.mesos.ContainerID\x12#\n\x07\x63ommand\x18\x02 \x01(\x0b\x32\x12.mesos.CommandInfo\x12 \n\x08tty_info\x18\x03 \x01(\x0b\x32\x0e.mesos.TtyInfo\x12\x13\n\x0binteractive\x18\x04 \x01(\x08\x1a\x41\n\x15\x41ttachContainerOutput\x12(\n\x0c\x63ontainer_id\x18\x01 \x02(\x0b\x32\x12.mesos.ContainerID\x1a\xd8\x01\n\x14\x41ttachContainerInput\x12\x39\n\x04type\x18\x01 \x01(\x0e\x32+.mesos.agent.Call.AttachContainerInput.Type\x12(\n\x0c\x63ontainer_id\x18\x02 \x01(\x0b\x32\x12.mesos.ContainerID\x12$\n\nprocess_io\x18\x03 \x01(\x0b\x32\x10.mesos.ProcessIO\"5\n\x04Type\x12\x0b\n\x07UNKNOWN\x10\x00\x12\x10\n\x0c\x43ONTAINER_ID\x10\x01\x12\x0e\n\nPROCESS_IO\x10\x02\"q\n\x04Type\x12\x0b\n\x07UNKNOWN\x10\x00\x12#\n\x1fLAUNCH_NESTED_CONTAINER_SESSION\x10\x11\x12\x1b\n\x17\x41TTACH_CONTAINER_OUTPUT\x10\x12\x12\x1a\n\x16\x41TTACH_CONTAINER_INPUT\x10\x13\x42 \n\x16org.apache.mesos.agentB\x06Protos')
  ,
  dependencies=[mesos_pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)



_CALL_ATTACHCONTAINERINPUT_TYPE = _descriptor.EnumDescriptor(
  name='Type',
  full_name='mesos.agent.Call.AttachContainerInput.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CONTAINER_ID', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='PROCESS_IO', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=683,
  serialized_end=736,
)
_sym_db.RegisterEnumDescriptor(_CALL_ATTACHCONTAINERINPUT_TYPE)

_CALL_TYPE = _descriptor.EnumDescriptor(
  name='Type',
  full_name='mesos.agent.Call.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='LAUNCH_NESTED_CONTAINER_SESSION', index=1, number=17,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ATTACH_CONTAINER_OUTPUT', index=2, number=18,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ATTACH_CONTAINER_INPUT', index=3, number=19,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=738,
  serialized_end=851,
)
_sym_db.RegisterEnumDescriptor(_CALL_TYPE)


_CALL_LAUNCHNESTEDCONTAINERSESSION = _descriptor.Descriptor(
  name='LaunchNestedContainerSession',
  full_name='mesos.agent.Call.LaunchNestedContainerSession',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='container_id', full_name='mesos.agent.Call.LaunchNestedContainerSession.container_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='command', full_name='mesos.agent.Call.LaunchNestedContainerSession.command', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='tty_info', full_name='mesos.agent.Call.LaunchNestedContainerSession.tty_info', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='interactive', full_name='mesos.agent.Call.LaunchNestedContainerSession.interactive', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=286,
  serialized_end=450,
)

_CALL_ATTACHCONTAINEROUTPUT = _descriptor.Descriptor(
  name='AttachContainerOutput',
  full_name='mesos.agent.Call.AttachContainerOutput',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='container_id', full_name='mesos.agent.Call.AttachContainerOutput.container_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=452,
  serialized_end=517,
)

_CALL_ATTACHCONTAINERINPUT = _descriptor.Descriptor(
  name='AttachContainerInput',
  full_name='mesos.agent.Call.AttachContainerInput',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='mesos.agent.Call.AttachContainerInput.type', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='container_id', full_name='mesos.agent.Call.AttachContainerInput.container_id', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='process_io', full_name='mesos.agent.Call.AttachContainerInput.process_io', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CALL_ATTACHCONTAINERINPUT_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=520,
  serialized_end=736,
)

_CALL = _descriptor.Descriptor(
  name='Call',
  full_name='mesos.agent.Call',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='launch_nested_container_session', full_name='mesos.agent.Call.launch_nested_container_session', index=0,
      number=9, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attach_container_output', full_name='mesos.agent.Call.attach_container_output', index=1,
      number=10, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attach_container_input', full_name='mesos.agent.Call.attach_container_input', index=2,
      number=11, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CALL_LAUNCHNESTEDCONTAINERSESSION, _CALL_ATTACHCONTAINEROUTPUT, _CALL_ATTACHCONTAINERINPUT, ],
  enum_types=[
    _CALL_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=42,
  serialized_end=851,
)

_CALL_LAUNCHNESTEDCONTAINERSESSION.fields_by_name['container_id'].message_type = mesos_pb2._CONTAINERID
_CALL_LAUNCHNESTEDCONTAINERSESSION.fields_by_name['command'].message_type = mesos_pb2._COMMANDINFO
_CALL_LAUNCHNESTEDCONTAINERSESSION.fields_by_name['tty_info'].message_type = mesos_pb2._TTYINFO
_CALL_LAUNCHNESTEDCONTAINERSESSION.containing_type = _CALL
_CALL_ATTACHCONTAINEROUTPUT.fields_by_name['container_id'].message_type = mesos_pb2._CONTAINERID
_CALL_ATTACHCONTAINEROUTPUT.containing_type = _CALL
_CALL_ATTACHCONTAINERINPUT.fields_by_name['type'].enum_type = _CALL_ATTACHCONTAINERINPUT_TYPE
_CALL_ATTACHCONTAINERINPUT.fields_by_name['container_id'].message_type = mesos_pb2._CONTAINERID
_CALL_ATTACHCONTAINERINPUT.fields_by_name['process_io'].message_type = mesos_pb2._PROCESSIO
_CALL_ATTACHCONTAINERINPUT.containing_type = _CALL
_CALL_ATTACHCONTAINERINPUT_TYPE.containing_type = _CALL_ATTACHCONTAINERINPUT
_CALL.fields_by_name['launch_nested_container_session'].message_type = _CALL_LAUNCHNESTEDCONTAINERSESSION
_CALL.fields_by_name['attach_container_output'].message_type = _CALL_ATTACHCONTAINEROUTPUT
_CALL.fields_by_name['attach_container_input'].message_type = _CALL_ATTACHCONTAINERINPUT
_CALL_TYPE.containing_type = _CALL
DESCRIPTOR.message_types_by_name['Call'] = _CALL

Call = _reflection.GeneratedProtocolMessageType('Call', (_message.Message,), dict(

  LaunchNestedContainerSession = _reflection.GeneratedProtocolMessageType('LaunchNestedContainerSession', (_message.Message,), dict(
    DESCRIPTOR = _CALL_LAUNCHNESTEDCONTAINERSESSION,
    __module__ = 'agent_pb2'
    # @@protoc_insertion_point(class_scope:mesos.agent.Call.LaunchNestedContainerSession)
    ))
  ,

  AttachContainerOutput = _reflection.GeneratedProtocolMessageType('AttachContainerOutput', (_message.Message,), dict(
    DESCRIPTOR = _CALL_ATTACHCONTAINEROUTPUT,
    __module__ = 'agent_pb2'
    # @@protoc_insertion_point(class_scope:mesos.agent.Call.AttachContainerOutput)
    ))
  ,

  AttachContainerInput = _reflection.GeneratedProtocolMessageType('AttachContainerInput', (_message.Message,), dict(
    DESCRIPTOR = _CALL_ATTACHCONTAINERINPUT,
    __module__ = 'agent_pb2'
    # @@protoc_insertion_point(class_scope:mesos.agent.Call.AttachContainerInput)
    ))
  ,
  DESCRIPTOR = _CALL,
  __module__ = 'agent_pb2'
  # @@protoc_insertion_point(class_scope:mesos.agent.Call)
  ))
_sym_db.RegisterMessage(Call)
_sym_db.RegisterMessage(Call.LaunchNestedContainerSession)
_sym_db.RegisterMessage(Call.AttachContainerOutput)
_sym_db.RegisterMessage(Call.AttachContainerInput)


DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), _b('\n\026org.apache.mesos.agentB\006Protos'))
# @@protoc_insertion_point(module_scope)
