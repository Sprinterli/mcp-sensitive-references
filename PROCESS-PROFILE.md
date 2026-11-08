# Sink profile `process-1`

**Status: Concept 0.7 draft, normative profile.** The conventions and terms of
[SPEC-DRAFT.md](SPEC-DRAFT.md#1-conventions) apply. This profile builds on the core documents and on
[RESOLVER-PROFILE.md](RESOLVER-PROFILE.md). It does not need any other document.

The sink gives plaintext values to a command that the host runs on the computer of the person. The
command reads each value at run time. The model-facing result keeps the references. The model does not see
a value, also not in the output of the command. The evidence for each rule is in
[protocol-package/PROFILE-process-1.md](protocol-package/PROFILE-process-1.md).

## 1. Preconditions

1. The host MUST resolve only if the negotiated intersection holds `process-1` and a resolver profile that
   the host supports. Version 1 defines one resolver profile, `oauth-resolver-1`.
2. The discovery object of the resolver profile MUST list `process-1` in `sink_profiles` and in `sinks`
   (RESOLVER-PROFILE.md, section 4). Else the host MUST NOT resolve. An operator-configured endpoint does
   not change this rule.
3. `process-1` requires a sink scope, the *process scope*. The discovery object names it in
   `sinks.process-1.scopes` and in `process_scope`. The host MUST resolve for this profile only with a
   resolver token that holds the resolve scope and the process scope.
4. The host MUST ask for the process scope only where it meets section 5 for every command that can
   receive a value. A host that cannot mask the output of commands on a platform MUST NOT ask for the
   process scope there.
5. The host MUST derive the destination from the command by section 3. The host MUST NOT take the
   destination from another model output.

## 2. Which references the sink resolves

1. The sink MUST resolve a reference only if the host observed it in a negotiated, authenticated result,
   and only if it has exactly one trusted issuer (HOST-INTEGRATION.md, section 3).
2. The sink MUST send a reference only to the resolve endpoint of its own issuer.
3. The sink MUST match references by exact code points. It MUST NOT normalize, case-fold, trim or rebuild
   a reference.
4. The sink SHOULD remove duplicate references before it sends a request.

Reference-shaped text without a trusted observation stays in the command as ordinary text. The host MUST
NOT send it to a resolver.

## 3. Wire values

The sink MUST send `sink_type` with the value `process` to the resolve endpoint.

The sink MUST send as `destination` the name of the program that the command runs. The name is the first
word of the command after any leading assignments of the form `NAME=value`. If that word is a path, the
sink SHOULD send its last part. The sink MUST NOT send the command line, an argument, an environment
value or a part of a value as `destination`. The destination MUST meet the rules of RESOLVER-PROFILE.md,
section 12.1.

This profile does not define how the host splits the command into words where the command has quotes,
escapes, a pipeline or a compound command. Section 7 names the effect.

## 4. When the sink resolves

1. The host MUST resolve only when the command reads the value. A command that the host, the client or the
   person refuses before it runs MUST cost no resolve request.
2. The host MUST resolve every reference of one command before the command gets any value. If one
   reference or one request fails, the command MUST get no value. The host MUST then stop the command, or
   MUST NOT start it. The host MUST NOT run the command with the reference text in place of a value
   without the knowledge of the person.
3. The host MUST give a value to the command through a channel that only the command reads, for example
   a pipe that the command opens. The host MUST NOT put the value into the command line. If the channel
   has a name in the file system, for example a named pipe, the host MUST create it with access for the
   owner only, in a directory that only the owner can open, and MUST give the value once, to one reader.

## 5. Output boundary

1. The host MUST mask the output of the command before the model sees it: the host replaces each value
   that it released for the command with its reference. This applies to the standard output, the error
   output, an error text of the host and every other text of the command run that the model can read.
2. Rule 1 applies also on the failure path: a non-zero exit status, a signal, a timeout and an error of the
   host. If the host cannot mask the output on a path, it MUST NOT give that output to the model.
3. The model-facing result MUST keep the references. It MUST NOT hold a resolved value.
4. The report of the sink MUST NOT contain protected data items 1 to 4 and 6 (SPEC-DRAFT.md, section 8).
   It MAY hold counts, a status, error codes and the program name.
5. While the session works, the host SHOULD also mask a released value in later tool output.

An echo guard can recognize a value only in known encodings (SECURITY-MODEL.md, section 6). A program that
transforms the value before it prints it can pass rule 1.

## 6. Server rules

1. The server MUST refuse `process` for a token without the process scope with `403 insufficient_scope`,
   before any lookup (RESOLVER-PROFILE.md, section 5.4).
2. The audit event of the server MUST keep of `destination` only a program name: the last path part of the
   destination if it holds no white space, else the fixed text `other`. The event MUST NOT keep a command
   line or an argument.
3. The consent page MUST name the process scope in one line that says that the program can put real values
   into commands that it runs on this computer, and that the program says it masks the command output
   before the AI sees it (RESOLVER-PROFILE.md, section 10.2).

## 7. Limit

The sink cannot protect a value against the program that receives it. The program can print the value in
a form that the host does not recognize, write it to a file or send it to the network.

The server trusts the program name that the host sends. It cannot check which program reads the value.
Any local process of the person that holds a resolver token with the process scope can get the full value
of every reference of that person. This is the reason why the process scope is a separate scope that a
person can leave out on the consent page.

A local process of the person that finds the channel of section 4, rule 3 can open it before the command
does. It then causes the resolve and reads the value without a token of its own. The access rules of that rule keep
out other users, not other processes of the same person.

The destination is advisory. The first word of a command is often not the program that reads the value:
for `cd dir && prog`, `env prog`, `sudo prog` or `bash -c '...'` the destination is `cd`, `env`, `sudo` or
`bash`, and for `printf %s <reference> | prog` it is `printf`. Hosts can also split words differently
(section 3). A server uses the destination for audit only (RESOLVER-PROFILE.md, section 12.1).

## 8. Not in this profile

- A sandbox or a shell policy for the command.
- A check of what the program does with the value.
- Commands on another computer than the computer of the host.

## 9. Evidence

**Note.** [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md) records the identifier under which the
reference server accepts this profile. The second host implements
it for the commands of a coding agent. The reference host implements it at demo level, on POSIX, tested
offline against the prototype issuer (`prototype/README.md`, section "Concept 0.7"). See
[IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).
