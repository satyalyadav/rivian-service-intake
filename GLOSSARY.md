# Service intake

A vehicle service center's intake step: an advisor takes a customer call, and the tool turns it into a technician write-up where every line is traceable to the call.

## Language

**Advisor**:
The service employee who takes the customer's call and produces the technician write-up.
_Avoid_: Agent, rep, CSR, user

**Customer**:
The vehicle owner who describes the problem on the call.
_Avoid_: Caller, client, driver

**Technician**:
The person who performs the repair and receives the write-up.
_Avoid_: Mechanic, tech

**Conversation**:
The customer call's content, one turn per line, as shown in the app.
_Avoid_: Transcript, source, dialogue, chat

**Turn**:
One speaker's line in the conversation.
_Avoid_: Message, utterance, entry

**Fact**:
A detail from the call, stored as a label and a value.
_Avoid_: Field, data point, item

**Correction**:
A value that a speaker replaces during the call. The write-up keeps both values and their order.
_Avoid_: Edit, fix, update

**Conflict**:
Two statements about the same detail that disagree, with no correction to resolve them.
_Avoid_: Discrepancy, mismatch, inconsistency

**Open question**:
Something the call left unknown that the advisor should ask before the visit.
_Avoid_: Follow-up, missing field

**Quote**:
The exact words from a turn that support a fact, a correction, or a conflict.
_Avoid_: Evidence, snippet, citation

**Vehicle context**:
VIN, model, year, and mileage supplied alongside the conversation.
_Avoid_: Vehicle info, metadata

**Technician write-up**:
The note delivered to the technician: facts, corrections, conflicts, and open questions, each tied to its quotes. It is a draft until the advisor passes it on.
_Avoid_: Handoff, draft handoff, note, summary, ticket

**Saved example**:
A conversation shipped with the app together with a checked result. It loads with no model call.
_Avoid_: Fixture, sample, demo data

**Live analysis**:
Running the model pipeline on the current conversation.
_Avoid_: Fresh request, run, analyze job
