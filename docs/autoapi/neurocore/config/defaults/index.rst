neurocore.config.defaults
=========================

.. py:module:: neurocore.config.defaults

.. autoapi-nested-parse::

   Built-in default values for NeuroCore configuration.

   These are the lowest-priority defaults. They are overridden by:
   neurocore.yaml → .env file → environment variables.



Attributes
----------

.. autoapisummary::

   neurocore.config.defaults.DEFAULT_PROJECT_NAME
   neurocore.config.defaults.DEFAULT_PROJECT_VERSION
   neurocore.config.defaults.DEFAULT_SKILLS_DIR
   neurocore.config.defaults.DEFAULT_BLUEPRINTS_DIR
   neurocore.config.defaults.DEFAULT_DATA_DIR
   neurocore.config.defaults.DEFAULT_LOGS_DIR
   neurocore.config.defaults.DEFAULT_LOG_LEVEL
   neurocore.config.defaults.DEFAULT_LOG_FORMAT
   neurocore.config.defaults.CONFIG_FILE_NAME
   neurocore.config.defaults.ENV_FILE_NAME
   neurocore.config.defaults.ENV_PREFIX


Module Contents
---------------

.. py:data:: DEFAULT_PROJECT_NAME
   :type:  str
   :value: 'my-agent'


.. py:data:: DEFAULT_PROJECT_VERSION
   :type:  str
   :value: '0.1.0'


.. py:data:: DEFAULT_SKILLS_DIR
   :type:  str
   :value: 'skills'


.. py:data:: DEFAULT_BLUEPRINTS_DIR
   :type:  str
   :value: 'blueprints'


.. py:data:: DEFAULT_DATA_DIR
   :type:  str
   :value: 'data'


.. py:data:: DEFAULT_LOGS_DIR
   :type:  str
   :value: 'logs'


.. py:data:: DEFAULT_LOG_LEVEL
   :type:  str
   :value: 'INFO'


.. py:data:: DEFAULT_LOG_FORMAT
   :type:  str
   :value: 'console'


.. py:data:: CONFIG_FILE_NAME
   :type:  str
   :value: 'neurocore.yaml'


.. py:data:: ENV_FILE_NAME
   :type:  str
   :value: '.env'


.. py:data:: ENV_PREFIX
   :type:  str
   :value: 'NEUROCORE_'


