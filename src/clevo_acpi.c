/*!
 * Copyright (c) 2020 TUXEDO Computers GmbH <tux@tuxedocomputers.com>
 *
 * This file is part of tuxedo-keyboard.
 *
 * tuxedo-keyboard is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software.  If not, see <https://www.gnu.org/licenses/>.
 */
#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt

#if defined(__clang__) || defined(__INTELLISENSE__) || defined(__CLANGD__)
#undef _Static_assert
#define _Static_assert(expr, ...)
#endif

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/acpi.h>
#include <linux/platform_device.h>
#include <linux/version.h>
#include "clevo_interfaces.h"

#define DRIVER_NAME			"clevo_acpi"

struct clevo_acpi_driver_data_t {
	struct acpi_device *adev;
	struct clevo_interface_t *clevo_interface;
};

static struct clevo_acpi_driver_data_t *active_driver_data = NULL;

static int clevo_acpi_evaluate(struct acpi_device *device, u8 cmd, u32 arg, union acpi_object **result)
{
	int status;
	acpi_handle handle;
	u64 dsm_rev_dummy = 0x00; // Dummy 0 value since not used
	u64 dsm_func = cmd;
	// Integer package data for argument
	union acpi_object dsm_argv4_package_data[] = {
		{
			.integer.type = ACPI_TYPE_INTEGER,
			.integer.value = arg
		}
	};

	// Package argument
	union acpi_object dsm_argv4 = {
		.package.type = ACPI_TYPE_PACKAGE,
		.package.count = 1,
		.package.elements = dsm_argv4_package_data
	};

	union acpi_object *out_obj;

	guid_t clevo_acpi_dsm_uuid;

	status = guid_parse(CLEVO_ACPI_DSM_UUID, &clevo_acpi_dsm_uuid);
	if (status < 0)
		return -ENOENT;

	handle = acpi_device_handle(device);
	if (handle == NULL)
		return -ENODEV;

	out_obj = acpi_evaluate_dsm(handle, &clevo_acpi_dsm_uuid, dsm_rev_dummy, dsm_func, &dsm_argv4);
	if (!out_obj) {
		pr_err("failed to evaluate _DSM\n");
		status = -1;
	}
	else {
		if (!IS_ERR_OR_NULL(result)) {
			*result = out_obj;
		}
	}

	return status;
}

static int clevo_acpi_interface_method_call(u8 cmd, u32 arg, union acpi_object **result_value)
{
	int status = 0;

	if (!IS_ERR_OR_NULL(active_driver_data)) {
		status = clevo_acpi_evaluate(active_driver_data->adev, cmd, arg, result_value);
	} else {
		pr_err("acpi method call exec, no driver data found\n");
		pr_err("..for method_call: %0#4x arg: %0#10x\n", cmd, arg);
		status = -ENODATA;
	}

	return status;
}

struct clevo_interface_t clevo_acpi_interface = {
	.string_id = CLEVO_INTERFACE_ACPI_STRID,
	.method_call = clevo_acpi_interface_method_call,
};

/*
 * ACPI notify handler — called by ACPICA for device notifications.
 * acpi_notify_handler signature: void (*)(acpi_handle, u32, void *)
 */
static void clevo_acpi_notify_handler(acpi_handle handle, u32 event, void *data)
{
	u32 event_value = 0;
	union acpi_object *out_obj;
	int status;
	struct acpi_device *device = (struct acpi_device *)data;

	status = clevo_acpi_evaluate(device, 0x01, 0, &out_obj);
	if (!status) {
		if (out_obj->type == ACPI_TYPE_INTEGER) {
			event_value = (u32)out_obj->integer.value;
		} else {
			pr_err("return type not integer, use clevo_evaluate_method2\n");
		}
		ACPI_FREE(out_obj);
	}
	pr_info("clevo_acpi notify: event=%0#6x, event_value=%0#6x\n", event, event_value);

	if (!IS_ERR_OR_NULL(clevo_acpi_interface.event_callb)) {
		u32 code_to_dispatch = event;
		if ((event == 0x02 || event == 0x80) && event_value != 0) {
			code_to_dispatch = event_value;
		}
		clevo_acpi_interface.event_callb(code_to_dispatch);
	}
}

#if LINUX_VERSION_CODE < KERNEL_VERSION(6, 2, 0)
/*
 * Old ACPI driver path (pre-kernel 6.2 API).
 * The old struct acpi_driver .add/.remove/.notify callbacks are used here.
 * This block is intentionally left for pre-6.2 kernels that still have
 * struct acpi_driver. For kernel >= 6.2 (and especially >= 7.x) we use
 * platform_driver + ACPI match table below.
 */

static int clevo_acpi_add_legacy(struct acpi_device *device)
{
	struct clevo_acpi_driver_data_t *driver_data;

	driver_data = devm_kzalloc(&device->dev, sizeof(*driver_data), GFP_KERNEL);
	if (!driver_data)
		return -ENOMEM;

	driver_data->adev = device;
	driver_data->clevo_interface = &clevo_acpi_interface;

	active_driver_data = driver_data;

	pr_debug("clevo_acpi driver add (legacy)\n");

	clevo_keyboard_add_interface(&clevo_acpi_interface);

	pr_info("interface initialized\n");

	return 0;
}

static int clevo_acpi_remove_legacy(struct acpi_device *device)
{
	pr_debug("clevo_acpi driver remove (legacy)\n");
	clevo_keyboard_remove_interface(&clevo_acpi_interface);
	active_driver_data = NULL;
	return 0;
}

static void clevo_acpi_notify_legacy(struct acpi_device *device, u32 event)
{
	u32 event_value = 0;
	union acpi_object *out_obj;
	int status;

	status = clevo_acpi_evaluate(device, 0x01, 0, &out_obj);
	if (!status) {
		if (out_obj->type == ACPI_TYPE_INTEGER) {
			event_value = (u32)out_obj->integer.value;
		} else {
			pr_err("return type not integer, use clevo_evaluate_method2\n");
		}
		ACPI_FREE(out_obj);
	}
	pr_debug("clevo_acpi event: %0#6x, clevo event value: %0#6x\n", event, event_value);

	if (!IS_ERR_OR_NULL(clevo_acpi_interface.event_callb)) {
		clevo_acpi_interface.event_callb(event);
	}
}

#ifdef CONFIG_PM
static int driver_suspend_callb(struct device *dev)
{
	pr_debug("driver suspend\n");
	return 0;
}

static int driver_resume_callb(struct device *dev)
{
	pr_debug("driver resume\n");
	return 0;
}

static SIMPLE_DEV_PM_OPS(clevo_driver_pm_ops, driver_suspend_callb, driver_resume_callb);
#endif

static const struct acpi_device_id clevo_acpi_device_ids[] = {
	{CLEVO_ACPI_RESOURCE_HID, 0},
	{"", 0}
};

static struct acpi_driver clevo_acpi_driver = {
	.name = DRIVER_NAME,
	.class = DRIVER_NAME,
	.ids = clevo_acpi_device_ids,
	.flags = ACPI_DRIVER_ALL_NOTIFY_EVENTS,
	.ops = {
		.add = clevo_acpi_add_legacy,
		.remove = clevo_acpi_remove_legacy,
		.notify = clevo_acpi_notify_legacy,
	},
#ifdef CONFIG_PM
	.drv.pm = &clevo_driver_pm_ops
#endif
};

module_acpi_driver(clevo_acpi_driver);

MODULE_DEVICE_TABLE(acpi, clevo_acpi_device_ids);

#else // LINUX_VERSION_CODE >= KERNEL_VERSION(6, 2, 0)

/*
 * Modern path: kernel >= 6.2 removed struct acpi_driver / module_acpi_driver.
 * Use platform_driver with ACPI device ID table and explicit notify handler
 * installation via acpi_dev_install_notify_handler().
 */

static const struct acpi_device_id clevo_acpi_device_ids[] = {
	{CLEVO_ACPI_RESOURCE_HID, 0},
	{"", 0}
};

MODULE_DEVICE_TABLE(acpi, clevo_acpi_device_ids);

static int clevo_acpi_platform_probe(struct platform_device *pdev)
{
	struct clevo_acpi_driver_data_t *driver_data;
	struct acpi_device *adev;
	int ret;

	adev = ACPI_COMPANION(&pdev->dev);
	if (!adev) {
		pr_err("No ACPI companion device found\n");
		return -ENODEV;
	}

	driver_data = devm_kzalloc(&pdev->dev, sizeof(*driver_data), GFP_KERNEL);
	if (!driver_data)
		return -ENOMEM;

	driver_data->adev = adev;
	driver_data->clevo_interface = &clevo_acpi_interface;
	platform_set_drvdata(pdev, driver_data);

	active_driver_data = driver_data;

	/* Install ACPI notify handler to receive firmware events */
	ret = acpi_dev_install_notify_handler(adev, ACPI_ALL_NOTIFY,
					      clevo_acpi_notify_handler, adev);
	if (ret) {
		pr_err("Failed to install ACPI notify handler: %d\n", ret);
		active_driver_data = NULL;
		return ret;
	}

	pr_debug("clevo_acpi driver probe\n");

	clevo_keyboard_add_interface(&clevo_acpi_interface);

	pr_info("interface initialized\n");

	return 0;
}

static void clevo_acpi_platform_remove(struct platform_device *pdev)
{
	struct clevo_acpi_driver_data_t *driver_data = platform_get_drvdata(pdev);

	pr_debug("clevo_acpi driver remove\n");

	if (driver_data && driver_data->adev) {
		acpi_dev_remove_notify_handler(driver_data->adev, ACPI_ALL_NOTIFY,
					       clevo_acpi_notify_handler);
	}

	clevo_keyboard_remove_interface(&clevo_acpi_interface);
	active_driver_data = NULL;
}

#ifdef CONFIG_PM_SLEEP
static int clevo_acpi_platform_suspend(struct device *dev)
{
	pr_debug("driver suspend\n");
	return 0;
}

static int clevo_acpi_platform_resume(struct device *dev)
{
	pr_debug("driver resume\n");
	return 0;
}

static SIMPLE_DEV_PM_OPS(clevo_acpi_platform_pm_ops,
			  clevo_acpi_platform_suspend,
			  clevo_acpi_platform_resume);
#define CLEVO_ACPI_PM_OPS (&clevo_acpi_platform_pm_ops)
#else
#define CLEVO_ACPI_PM_OPS NULL
#endif

static struct platform_driver clevo_acpi_platform_driver = {
	.probe  = clevo_acpi_platform_probe,
	.remove = clevo_acpi_platform_remove,
	.driver = {
		.name           = DRIVER_NAME,
		.owner          = THIS_MODULE,
		.acpi_match_table = ACPI_PTR(clevo_acpi_device_ids),
		.pm             = CLEVO_ACPI_PM_OPS,
	},
};

module_platform_driver(clevo_acpi_platform_driver);

#endif // LINUX_VERSION_CODE

MODULE_AUTHOR("TUXEDO Computers GmbH <tux@tuxedocomputers.com>");
MODULE_DESCRIPTION("Driver for Clevo ACPI interface");
MODULE_VERSION("0.1.2");
MODULE_LICENSE("GPL");
