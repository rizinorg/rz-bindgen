// SPDX-FileCopyrightText: 2022 wingdeans <wingdeans@protonmail.com>
// SPDX-License-Identifier: LGPL-3.0-only

#ifndef CUTTER_RZ_BINDINGS_H
#define CUTTER_RZ_BINDINGS_H

#include <CutterPlugin.h>

class CutterRzBindings : public QObject, CutterPlugin {
        Q_OBJECT
        Q_PLUGIN_METADATA(IID "re.rizin.cutter.plugins.rz-ghidra")
        Q_INTERFACES(CutterPlugin)

      public:
        void setupPlugin() override;
        void setupInterface(MainWindow *main) override;

        QString getName() const override { return "CutterRzBindings"; }
        QString getAuthor() const override { return "wingdeans"; }
        QString getDescription() const override {
                return "exposes Rizin APIs to Python";
        }
        QString getVersion() const override { return "0.0.1"; }
};

#endif
