# ASHRAE 62.1-2016 table structures

Status: draft PR scaffold; implementation not started.

## Depends on

`ashrae-62.1-2016/structural-inventory`

## Purpose

Begin the table-hardening lane using measured whole-document denominators.

## Scope

- table-region identity and parent provision
- row, column, and header reconstruction
- spanning-header diagnostics
- units, notes, footnotes, and continuation state
- source coordinates and deterministic table locators
- private exact-source measurement of recognized versus unsupported tables

## Boundaries

Do not convert source categories into a universal taxonomy or treat rectangular extraction as reviewed semantic table meaning.

## Completion gate

Measured structural table support is reported against the exact retained artifact with explicit unsupported cases. Remove this scaffold when implementation replaces it.
