neurocore.skills.base.SkillMeta
===============================

.. py:class:: neurocore.skills.base.SkillMeta

   Declarative metadata for a Skill.

   Frozen dataclass — immutable once created. Describes what a skill
   is, what it needs, and what it provides.

   .. attribute:: name

      Unique skill identifier (e.g. "neuroweave", "web-search").

   .. attribute:: version

      Semantic version string (e.g. "0.1.0").

   .. attribute:: description

      Human-readable description.

   .. attribute:: author

      Author or maintainer name.

   .. attribute:: requires

      pip package dependencies (e.g. ["anthropic>=0.42"]).

   .. attribute:: provides

      Context keys this skill produces.

   .. attribute:: consumes

      Context keys this skill reads.

   .. attribute:: config_schema

      JSON Schema dict for validating skill config.

   .. attribute:: tags

      Categorization tags (e.g. ["memory", "graph", "llm"]).


   .. py:attribute:: name
      :type:  str


   .. py:attribute:: version
      :type:  str


   .. py:attribute:: description
      :type:  str
      :value: ''



   .. py:attribute:: author
      :type:  str
      :value: ''



   .. py:attribute:: requires
      :type:  list[str]
      :value: []



   .. py:attribute:: provides
      :type:  list[str]
      :value: []



   .. py:attribute:: consumes
      :type:  list[str]
      :value: []



   .. py:attribute:: config_schema
      :type:  dict[str, Any]


   .. py:attribute:: tags
      :type:  list[str]
      :value: []


